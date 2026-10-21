#!/usr/bin/env python3
"""Cross-check PRIVATE FCEUX $E8DE execution callbacks against CPU writes.

Reports only source-free aggregate evidence. Do not upload the input logs, ROM,
FM2, PPU snapshots, palette data or derived copyrighted images.
This confirms execution/write provenance, NOT display-effective PPU scroll.
"""
import argparse
import csv
import json
from pathlib import Path
import re

HEX2=re.compile(r"[0-9A-Fa-f]{2}\Z")
HEX4=re.compile(r"[0-9A-Fa-f]{4}\Z")
DEC=re.compile(r"(?:0|[1-9][0-9]*)\Z")
EXEC_FIELDS=["frame","cycle","ram_0b","ram_0c","ram_0d"]
COUNT_FIELDS=["frame","exec_hits"]
EVENT_FIELDS=["frame","cycles","address","value","kind"]
WITNESS_FIELDS={
 "format","first_observed_frame","last_observed_frame","frame_gaps",
 "exec_callback_count","rom_identity_verified","movie_readonly_verified"
}


def _file(path,max_bytes):
    p=Path(path)
    if p.is_symlink() or not p.is_file() or not 0<p.stat().st_size<=max_bytes:
        raise ValueError("private input missing, symlinked or oversized")
    return p


def _num(value,kind):
    if not isinstance(value,str) or DEC.fullmatch(value) is None:
        raise ValueError("noncanonical numeric "+kind)
    return int(value)


def _hex(value,pattern,kind):
    if not isinstance(value,str) or pattern.fullmatch(value) is None:
        raise ValueError("invalid hex "+kind)
    return int(value,16)


def _rows(path,columns,max_bytes,max_rows):
    result=[]
    with _file(path,max_bytes).open("r",encoding="ascii",newline="") as f:
        reader=csv.DictReader(f,delimiter="\t")
        if reader.fieldnames!=columns: raise ValueError("private TSV schema mismatch")
        for row in reader:
            if len(result)>=max_rows or set(row)!=set(columns) or any(
                    v is None for v in row.values()):
                raise ValueError("malformed or oversized private TSV")
            result.append(row)
    return result


def _witness(path,start,stop):
    fields={}
    for line in _file(path,4096).read_text(encoding="ascii").splitlines():
        if "=" not in line: raise ValueError("invalid private witness line")
        key,value=line.split("=",1)
        if key in fields: raise ValueError("duplicate private witness key")
        fields[key]=value
    if fields.keys()!=WITNESS_FIELDS or fields["format"]!="private_e8de_emitter_exec_v1":
        raise ValueError("private execution witness version mismatch")
    if fields["rom_identity_verified"]!="yes" or fields["movie_readonly_verified"]!="yes":
        raise ValueError("original movie/ROM identity unverified")
    if _num(fields["first_observed_frame"],"first frame") not in (0,1):
        raise ValueError("movie execution hook attached late")
    if _num(fields["last_observed_frame"],"last frame")!=stop:
        raise ValueError("movie execution witness did not reach the stop frame")
    if _num(fields["frame_gaps"],"frame gaps")!=0:
        raise ValueError("movie callback sequence has gaps")
    return _num(fields["exec_callback_count"],"execution calls")


def audit(execs,counts,events,witness,*,start=600,stop=920):
    if (type(start)is not int or type(stop)is not int or start<1 or
        stop<start or stop-start>1200):
        raise ValueError("invalid private frame window")
    n=stop-start+1
    reported_calls=_witness(witness,start,stop)
    execution=_rows(execs,EXEC_FIELDS,2*1024*1024,1201)
    count_rows=_rows(counts,COUNT_FIELDS,100000,1201)
    if len(execution)!=n or len(count_rows)!=n or reported_calls!=n:
        raise ValueError("execution callback count is incomplete")
    selected={}
    previous_cycle=-1
    for index,(row,counter) in enumerate(zip(execution,count_rows)):
        frame=start+index
        if (_num(row["frame"],"execution frame")!=frame or
            _num(counter["frame"],"count frame")!=frame or
            _num(counter["exec_hits"],"execution hits")!=1):
            raise ValueError("missing, duplicated or misordered emitter call")
        cycle=_num(row["cycle"],"execution cycle")
        if cycle<=previous_cycle:
            raise ValueError("execution CPU cycles not increasing")
        previous_cycle=cycle
        selected[frame]=(cycle,
                         _hex(row["ram_0b"],HEX2,"RAM $0B"),
                         _hex(row["ram_0c"],HEX2,"RAM $0C"),
                         _hex(row["ram_0d"],HEX2,"RAM $0D"))
    writes={f:[] for f in selected}
    previous_frame=-1
    for row in _rows(events,EVENT_FIELDS,64*1024*1024,500000):
        frame=_num(row["frame"],"event frame")
        if frame<previous_frame: raise ValueError("CPU events out of frame order")
        previous_frame=frame
        if frame not in writes: continue
        cycle=_num(row["cycles"],"event cycle")
        address=_hex(row["address"],HEX4,"register address")
        value=_hex(row["value"],HEX2,"register value")
        kind=row["kind"]
        if kind not in ("R","W"):raise ValueError("invalid event kind")
        if kind=="W" and address in (0x2000,0x2005):
            writes[frame].append((cycle,address,value))
    seen_zero_after=0
    for frame,(exec_cycle,ram0b,ram0c,ram0d) in selected.items():
        all_writes=writes[frame]
        ctrl=[(cycle,value) for cycle,addr,value in all_writes if addr==0x2000]
        scroll=[(cycle,value) for cycle,addr,value in all_writes if addr==0x2005]
        if len(scroll)!=4:
            raise ValueError("expected four observed $2005 writes per frame")
        if not any(cycle==exec_cycle+9 and (value&1)==(ram0c&1)
                   for cycle,value in ctrl):
            raise ValueError("emitter PPUCTRL write or $0C nametable bit mismatch")
        if (scroll[:2]!=[(exec_cycle+20,ram0b),(exec_cycle+27,ram0d)]):
            raise ValueError("emitter RAM input does not match timed $2005 writes")
        if scroll[2][0]<=scroll[1][0] or scroll[3][0]<=scroll[2][0]:
            raise ValueError("late $2005 writes are not chronologically separate")
        if scroll[2][1:]!=(0,) or scroll[3][1:]!=(0,):
            raise ValueError("late $2005 writes are not the observed zero reset pair")
        seen_zero_after+=1
    return {
        "classification":"PRIVATE verified CPU execution provenance, NOT rendered scroll",
        "first_frame":start,"last_frame":stop,"checked_frames":n,
        "emitter_address":"$E8DE",
        "observed_emitter_executions":len(execution),
        "emitter_executions_per_frame":1,
        "ppu_control_write_latency_cpu_cycles":9,
        "first_ppuscroll_write_latency_cpu_cycles":20,
        "second_ppuscroll_write_latency_cpu_cycles":27,
        "first_ppuscroll_source":"RAM $0B at emitter execution",
        "second_ppuscroll_source":"RAM $0D at emitter execution",
        "nametable_low_bit_source":"RAM $0C at emitter execution",
        "matching_emitter_register_sequence_frames":n,
        "observed_later_zero_scroll_write_frames":seen_zero_after,
        "callback_frame_gaps":0,
        "rom_identity_verified":True,"fm2_readonly_verified":True,
        "ppu_status_read_latch_verified":False,
        "display_effective_scroll_verified":False,
        "car_camera_speed_verified":False,
        "full_movie_terminal_verified":False,
        "original_rom_or_graphics_in_report":False
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_execution_tsv",type=Path)
    parser.add_argument("private_count_tsv",type=Path)
    parser.add_argument("private_cpu_video_tsv",type=Path)
    parser.add_argument("private_terminal_witness",type=Path)
    parser.add_argument("--start",type=int,default=600)
    parser.add_argument("--stop",type=int,default=920)
    args=parser.parse_args()
    try:
        result=audit(args.private_execution_tsv,args.private_count_tsv,
                     args.private_cpu_video_tsv,args.private_terminal_witness,
                     start=args.start,stop=args.stop)
    except (OSError,ValueError,UnicodeError) as exc:
        parser.exit(1,"PRIVATE_E8DE_PROVENANCE_INCONCLUSIVE: "+str(exc)+"\n")
    print("PRIVATE_E8DE_RUNTIME_PROVENANCE_PASS")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
