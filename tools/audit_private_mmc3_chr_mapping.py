#!/usr/bin/env python3
"""Audit selected MMC3 CHR banks in PRIVATE FCEUX CPU register-write traces.

$8000/$8001 mapping writes are evidence of a mapper selection, not proof
that an 8x8 tile was rendered. Never report source ROM bytes or screenshots.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from audit_fceux_trace_alignment import video_events
from audit_private_nes_variant_banks import read_layout

MMC3_CHR_REGISTERS=frozenset(range(6))
MAX_CHR_1KB_BANKS=4096


def selected_banks(register,raw_bank,bank_count):
    if not 0<=register<6 or not 0<=raw_bank<=255:
        raise ValueError("invalid MMC3 CHR register or bank")
    if not 1<=bank_count<=MAX_CHR_1KB_BANKS:
        raise ValueError("invalid CHR bank count")
    # MMC3 R0/R1 select paired 2KiB CHR ROM banks; bit zero ignored.
    if register<2:
        bank=raw_bank&0xfe
        return tuple(sorted({bank%bank_count,(bank+1)%bank_count}))
    return (raw_bank%bank_count,)


def analyze_trace(path,*,bank_count=128,focus_banks=(124,125,126),frame_interval=1803):
    if not 1<=bank_count<=MAX_CHR_1KB_BANKS:
        raise ValueError("invalid CHR bank count")
    if not 1<=frame_interval<=120000:
        raise ValueError("invalid timeline frame interval")
    focus=tuple(sorted(set(focus_banks)))
    if len(focus)>64 or any(not isinstance(x,int) or not 0<=x<bank_count for x in focus):
        raise ValueError("target banks exceed supported CHR layout")
    last_select=None
    count=0
    chr_writes=0
    ignored_data=0
    last_frame=None
    sightings=defaultdict(lambda:{"count":0,"first_frame":None,"last_frame":None,"intervals":set(),"registers":set()})
    inverted_writes=0
    for frame,address,value in video_events(Path(path)):
        count+=1
        if address=="8000":
            last_select=int(value,16)
        elif address=="8001":
            if last_select is None:
                ignored_data+=1
                continue
            reg=last_select&7
            if reg not in MMC3_CHR_REGISTERS:
                ignored_data+=1
                continue
            if last_select&0x40:
                inverted_writes+=1
            banks=selected_banks(reg,int(value,16),bank_count)
            chr_writes+=1
            for bank in banks:
                if bank not in focus:
                    continue
                t=sightings[bank]
                t["count"]+=1
                if t["first_frame"] is None:
                    t["first_frame"]=frame
                t["last_frame"]=frame
                t["intervals"].add(frame//frame_interval)
                t["registers"].add(reg)
        last_frame=frame
    report=[]
    for bank in focus:
        t=sightings.get(bank)
        report.append({
            "bank":bank,
            "mapping_write_count":0 if t is None else t["count"],
            "first_mapping_frame":None if t is None else t["first_frame"],
            "last_mapping_frame":None if t is None else t["last_frame"],
            "candidate_movie_intervals":[] if t is None else sorted(t["intervals"]),
            "registers_that_selected_bank":[] if t is None else sorted(t["registers"])
        })
    return {
        "classification":"private mapper register-write trace, CHR mapping candidates only",
        "frame_interval":frame_interval,
        "captured_event_count":count,
        "last_observed_event_frame":last_frame,
        "valid_chr_mapping_data_writes":chr_writes,
        "inverted_chr_mode_writes":inverted_writes,
        "unattributed_or_non_chr_data_writes":ignored_data,
        "focus_bank_reports":report,
        "source_rom_layout_proven":False,
        "actual_ppu_rendered_bank_proven":False,
        "original_stage_identity_proven":False,
        "complete_movie_replay_proven":False,
        "next_step":"Correlate selected bank windows with validated private PPU snapshots and original rendered frames."
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_mmc3_video_writes",type=Path)
    p.add_argument("--private-rom",type=Path,
                   help="owner-supplied ROM for checked CHR size and MMC3 identity")
    p.add_argument("--target-banks",default="124,125,126",
                   help="numeric comma-separated 1KiB CHR ROM banks")
    p.add_argument("--frame-interval",type=int,default=1803)
    args=p.parse_args()
    try:
        target=tuple(int(k) for k in args.target_banks.split(","))
        count=128
        if args.private_rom:
            layout=read_layout(args.private_rom)
            if layout["mapper"]!=4:
                raise ValueError("CHR mapper trace requires a Mapper 4 ROM")
            count=len(layout["chr"])//1024
        result=analyze_trace(args.private_mmc3_video_writes,
                             bank_count=count,focus_banks=target,
                             frame_interval=args.frame_interval)
        result["source_rom_layout_proven"]=bool(args.private_rom)
    except (ValueError,OSError,UnicodeError) as exc:
        p.exit(1,"PRIVATE_MMC3_CHR_TRACE_INCONCLUSIVE: "+str(exc)+"\n")
    print("PRIVATE_MMC3_CHR_TRACE_PREFLIGHT_PASS")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
