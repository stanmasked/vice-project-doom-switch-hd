#!/usr/bin/env python3
"""Audit PRIVATE FCEUX frame-phase observations without claiming exact scanlines.

Input: read-only original FM2 'registerafter' CPU cycle markers, and CPU
instruction callback cycles for the four verified $2005 writers.
The output contains only aggregate timing, not ROM, movie, image, or traces.
"""
import argparse
import csv
import json
from pathlib import Path
from statistics import mean

MAX_CYCLES=1_000_000_000_000
COLUMNS_ANCHOR=["frame","cycle"]
COLUMNS_WRITER=["frame","cycle","pc"]
WRITERS=["E8EC","E8F1","E369","E36C"]


def _read_tsv(path,header,maximum):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=8*1024*1024:
        raise ValueError("invalid private input file")
    output=[]
    with path.open("r",encoding="ascii",newline="") as handle:
        reader=csv.DictReader(handle,delimiter="\t")
        if reader.fieldnames!=header:
            raise ValueError("private TSV schema mismatch")
        for row in reader:
            if len(output)>=maximum or set(row)!=set(header) or any(v is None for v in row.values()):
                raise ValueError("malformed or oversized private TSV")
            output.append(row)
    return output


def _number(text,kind):
    if not isinstance(text,str) or not text.isascii() or not text.isdecimal() or text!=str(int(text)):
        raise ValueError("noncanonical numeric "+kind)
    number=int(text)
    if not 0<=number<=MAX_CYCLES:
        raise ValueError("out-of-range "+kind)
    return number


def _witness(path,expected_format,expected_stop,callback_field):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=4096:
        raise ValueError("invalid private witness")
    fields={}
    for line in path.read_text(encoding="ascii").splitlines():
        if "=" not in line:raise ValueError("malformed private witness")
        k,v=line.split("=",1)
        if k in fields:raise ValueError("duplicate private witness field")
        fields[k]=v
    if (fields.get("format")!=expected_format or
        _number(fields.get("first_observed_frame",""),"first callback frame") not in (0,1) or
        _number(fields.get("last_observed_frame",""),"last callback frame")<expected_stop or
        _number(fields.get("frame_gaps",""),"frame gaps")!=0 or
        fields.get("rom_identity_verified")!="yes" or
        fields.get("movie_readonly_verified")!="yes"):
        raise ValueError("private original movie provenance incomplete")
    if callback_field is not None:
        return _number(fields.get(callback_field,""),callback_field)


def audit(frame_anchor,frame_witness,writer_pcs,writer_witness,
          *,start=600,stop=920,late_spread_limit=32):
    if (type(start)is not int or type(stop)is not int or
        start<2 or stop<start or stop-start>1200 or
        type(late_spread_limit)is not int or not 1<=late_spread_limit<=128):
        raise ValueError("invalid frame-phase audit bounds")
    _witness(frame_witness,"private_original_fceux_frame_anchor_v1",stop,None)
    if (_witness(writer_witness,"private_ppuscroll_writer_pc_v1",stop,
                 "writer_pc_hits") != 4*(stop-start+1)):
        raise ValueError("private writer callback witness count mismatch")
    anchors={}
    last_frame=-1
    last_cycle=-1
    for row in _read_tsv(frame_anchor,COLUMNS_ANCHOR,2000):
        frame=_number(row["frame"],"anchor frame")
        cycle=_number(row["cycle"],"anchor CPU cycle")
        if frame<=last_frame or cycle<=last_cycle:
            raise ValueError("frame anchors are not strictly increasing")
        anchors[frame]=cycle
        last_frame,last_cycle=frame,cycle
    for frame in range(start-1,stop+1):
        if frame not in anchors:
            raise ValueError("missing continuous original frame anchor")
    writers={}
    last_frame=-1
    last_cycle=-1
    for row in _read_tsv(writer_pcs,COLUMNS_WRITER,5000):
        frame=_number(row["frame"],"writer frame")
        cycle=_number(row["cycle"],"writer cycle")
        if frame<last_frame or cycle<=last_cycle:
            raise ValueError("writer callback cycles not strictly ordered")
        pc=row["pc"].upper()
        if len(pc)!=4 or any(c not in "0123456789ABCDEF" for c in pc):
            raise ValueError("invalid writer PC address")
        writers.setdefault(frame,[]).append((cycle,pc))
        last_frame,last_cycle=frame,cycle
    phase_early=[]
    phase_late=[]
    pair_early=[]
    pair_late=[]
    for frame in range(start,stop+1):
        selected=writers.get(frame)
        if selected is None or [pc for _,pc in selected]!=WRITERS:
            raise ValueError("incomplete or misordered original $2005 writer callback sequence")
        prev,cur=anchors[frame-1],anchors[frame]
        if not all(prev<cycle<cur for cycle,_ in selected):
            raise ValueError("different CPU-cycle epochs or writer outside frame anchors")
        e0,e1,l0,l1=[cycle for cycle,_ in selected]
        phase_early.append(e0-prev)
        phase_late.append(l0-prev)
        pair_early.append(e1-e0)
        pair_late.append(l1-l0)
    if set(pair_early)!={7} or set(pair_late)!={4}:
        raise ValueError("emitter or late PPU writer pair latency changed")
    late_spread=max(phase_late)-min(phase_late)
    early_spread=max(phase_early)-min(phase_early)
    if late_spread>late_spread_limit:
        raise ValueError("late $2005 writer is not in a stable frame-relative phase")
    periods=[anchors[i]-anchors[i-1] for i in range(start,stop+1)]
    return {
      "schema":"private_fceux_stage1_writer_frame_phase_v1",
      "classification":"verified CPU writer/callback timing; NOT PPU scanline or camera speed",
      "window":{"start_frame":start,"stop_frame":stop,"frames":stop-start+1},
      "after_frame_cpu_period":{"min":min(periods),"max":max(periods),
                                 "mean":round(mean(periods),4)},
      "early_2005_since_previous_frame_callback_cycles":{
          "min":min(phase_early),"max":max(phase_early),"spread":early_spread},
      "late_e369_since_previous_frame_callback_cycles":{
          "min":min(phase_late),"max":max(phase_late),"spread":late_spread},
      "late_e369_until_current_frame_callback_cycles":{
          "min":min(anchors[f]-writers[f][2][0] for f in range(start,stop+1)),
          "max":max(anchors[f]-writers[f][2][0] for f in range(start,stop+1))},
      "early_writer_pair_cycles":7,"late_writer_pair_cycles":4,
      "callback_frame_gaps":0,
      "late_writer_phase_stability_verified":True,
      "absolute_scanline_verified":False,
      "ppu_irq_execution_verified":False,
      "visible_display_scroll_verified":False,
      "road_camera_velocity_verified":False,
      "cross_session_cpu_clock_epoch_assumed_compatible":True,
      "limitations":[
        "FCEUX frame callback CPU cycle is not a calibrated PPU dot/scanline origin",
        "Frame-anchor and writer-PC captures are independent runs; cycles must share a common reset epoch",
        "Stable timing does not by itself identify NMI, MMC3 IRQ, or sprite-zero split",
        "Raw private execution traces, FM2, ROM and graphics must never be committed"
      ]
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_frame_anchor_tsv",type=Path)
    parser.add_argument("private_frame_anchor_witness",type=Path)
    parser.add_argument("private_writer_pc_tsv",type=Path)
    parser.add_argument("private_writer_witness",type=Path)
    parser.add_argument("--start",type=int,default=600)
    parser.add_argument("--stop",type=int,default=920)
    args=parser.parse_args()
    try:
        result=audit(args.private_frame_anchor_tsv,args.private_frame_anchor_witness,
                     args.private_writer_pc_tsv,args.private_writer_witness,
                     start=args.start,stop=args.stop)
    except (OSError,ValueError,UnicodeError) as error:
        parser.exit(1,"PRIVATE_FRAME_PHASE_INCONCLUSIVE: "+str(error)+"\n")
    print("PRIVATE_STAGE1_FRAME_PHASE_AUDIT_PASS")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
