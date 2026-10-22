#!/usr/bin/env python3
"""Compare TWO sealed private source replays without publishing source data.

Compare fully validated fresh road RGB and FCEUX CPU/PPU values by
movie frame, normalizing absolute CPU clock epochs. Identical captures
in two directories are *not*, by themselves, proof of two executions.
For genuinely orchestrated distinct process launches, use --execute.
Never output private images, raw PPU traces, full ROM/FM2 SHA-256,
source screen-coordinate series, absolute CPU clocks or paths.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from audit_private_road_ppu_321_frame_phase import CLOCK_FIELDS
from audit_private_road_ppu_321_trace import rows,num
from build_private_road_ppu_join import (
    audit as source_audit,derive_documents
)
from run_private_road_ppu_321 import launch
from seal_private_road_ppu_321 import private_dir

def _digest(path:Path)->bytes:
    # Called only after original ROM/FM2 SHA-256 artifact-seal audit.
    if path.is_symlink() or not path.is_file():
        raise ValueError("private RGB evidence missing or symlinked")
    sha=hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):
            sha.update(part)
    return sha.digest()

def _durations(directory:Path)->tuple[int,...]:
    times=rows(directory/"road_321_frame_clock.tsv",CLOCK_FIELDS,321)
    intervals=[]
    for index,r in enumerate(times):
        if num(r["frame"],"frame")!=600+index:
            raise ValueError("movie frame clock indices differ")
        start=num(r["begin_cycle"],"frame start")
        end=num(r["end_cycle"],"frame end")
        if end<=start:raise ValueError("CPU frame clock did not advance")
        intervals.append(end-start)
    return tuple(intervals)

def compare(rom:Path,movie:Path,legacy:Path,first:Path,second:Path)->dict:
    # Fail closed on absent, non-directory, symlinked or public-checkout
    # inputs before any original source data is parsed. In particular,
    # pathlib.resolve(strict=True) exposes FileNotFoundError to callers.
    # The privacy validator provides a consistent ValueError instead.
    first=private_dir(first)
    second=private_dir(second)
    if first==second:
        raise ValueError("two captures must be in distinct private directories")
    # Independently rerun the full Stage186 SHA-sealed source-provenance
    # RGB/PPU original numeric join for EACH capture.
    one=source_audit(rom,movie,first,legacy)
    two=source_audit(rom,movie,second,legacy)
    if one!=two or not one["original_same_session_ppu_rgb_numeric_join_checked"]:
        raise ValueError("one source RGB+PPU full-window join failed")
    road_a,ppu_a=derive_documents(first)
    road_b,ppu_b=derive_documents(second)
    if road_a!=road_b:
        raise ValueError("two source image-space interval series differ")
    if ppu_a!=ppu_b:
        raise ValueError("two CPU writer values, RAM or relative phases differ")
    if _durations(first)!=_durations(second):
        raise ValueError("two recorded FCEUX frame CPU lengths differ")
    if _digest(first/"road_321_rgb_scanlines.bin")!=_digest(
            second/"road_321_rgb_scanlines.bin"):
        raise ValueError("road RGB source pixels differ even when masks agree")
    # CPU absolute cycle counters may have a per-process epoch offset.
    # They are not directly comparable across two replays.
    return {
        "source_road_rgb_samples_compared":41,
        "source_cpu_frames_compared":321,
        "source_cpu_writer_values_and_phases_compared":1284,
        "accepted_source_road_cross_sections":37,
        "ambiguous_source_road_cross_sections":4,
        "source_raw_rgb_scanline_bytes_identical":True,
        "absolute_cpu_cycle_clock_epoch_assumed_identical":False,
        "two_source_directories_verified":True,
        "two_independent_fceux_processes_proven_by_existing_files":False,
        "original_effective_ppu_scroll_proven":False,
        "original_road_camera_speed_proven":False,
        "original_road_collision_proven":False,
        "source_media_or_hashes_in_report":False,
    }

def run_and_compare(rom:Path,movie:Path,legacy:Path,
                    first:Path,second:Path,
                    executable:str="fceux",watchdog:int=1800)->dict:
    # Only this mode actually invokes two separate local emulator processes.
    # The source-only FCEUX launcher rejects existing capture locations.
    if first.resolve()==second.resolve():
        raise ValueError("cannot run two captures into the same target")
    launch(rom,movie,first,fceux=executable,timeout_seconds=watchdog)
    launch(rom,movie,second,fceux=executable,timeout_seconds=watchdog)
    result=compare(rom,movie,legacy,first,second)
    return {**result,
            "two_separate_fceux_processes_launched_by_this_command":True}

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom",required=True,type=Path)
    parser.add_argument("--movie",required=True,type=Path)
    parser.add_argument("--legacy-numeric-report",required=True,type=Path)
    parser.add_argument("--capture-a",required=True,type=Path)
    parser.add_argument("--capture-b",required=True,type=Path)
    parser.add_argument("--execute",action="store_true",
                        help="actually launch FCEUX separately into two new private dirs")
    parser.add_argument("--fceux",default="fceux")
    parser.add_argument("--timeout-seconds",type=int,default=1800)
    args=parser.parse_args()
    if args.execute:
        result=run_and_compare(args.rom,args.movie,
              args.legacy_numeric_report,args.capture_a,args.capture_b,
              args.fceux,args.timeout_seconds)
    else:
        result=compare(args.rom,args.movie,args.legacy_numeric_report,
                       args.capture_a,args.capture_b)
    print("VPD_PRIVATE_DUAL_ROAD_PPU_REPLAY_PASS"
          " source_rgb_slots=41 road_valid=37 road_ambiguous=4"
          " cpu_frames=321 cpu_writer_phases=1284"
          " same_original_file_ids=yes"
          " fresh_processes_launched_by_command=" +
          ("yes" if result.get(
            "two_separate_fceux_processes_launched_by_this_command")
             else "not_verified")
          +" effective_ppu_scroll_proven=no"
          " original_road_camera_collision_proven=no"
          " private_source_data_disclosed=no")

if __name__=="__main__":main()
