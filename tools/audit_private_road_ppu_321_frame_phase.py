#!/usr/bin/env python3
"""Private exact-frame CPU writer phase from FCEUX frame-begin clocks.

All per-frame writer/begin/end cycles remain entirely on the owner's
machine; output is a numeric-free, source-free aggregate. A source
CPU frame phase does not prove PPU raster scroll or physical camera speed.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from audit_private_road_ppu_321_trace import (
    audit as validate_raw, rows, num, hexn, HEX2, W_FIELDS,
    START, STOP, PCS, ANCHORS,
)

CLOCK_FIELDS=["frame","begin_cycle","end_cycle"]
EARLY_LOW,EARLY_HIGH=793,2212
LATE_LOW,LATE_HIGH=24283,24291
# A frame has roughly 29.8k NTSC CPU cycles, but never assert a
# particular console's exact frame duration without source evidence.
MAX_FRAME_CPU_CYCLES=40000
MIN_FRAME_CPU_CYCLES=25000

def validate_clocked_capture(directory:Path)->dict:
    base=validate_raw(directory) # all 1284 original-free structure checks
    writers=rows(directory/"road_321_writers.tsv",W_FIELDS,1284)
    clocks=rows(directory/"road_321_frame_clock.tsv",CLOCK_FIELDS,321)
    previous_begin=None
    previous_end=None
    observed_first=[]
    observed_late=[]
    for index,clock in enumerate(clocks):
        frame=START+index
        if num(clock["frame"],"frame index")!=frame:
            raise ValueError("missing, duplicated or unordered frame clock")
        begin=num(clock["begin_cycle"],"real begin timestamp")
        end=num(clock["end_cycle"],"real after timestamp")
        duration=end-begin
        if not MIN_FRAME_CPU_CYCLES<=duration<=MAX_FRAME_CPU_CYCLES:
            raise ValueError("frame cycle duration unavailable/incompatible")
        if previous_begin is not None and begin<=previous_begin:
            raise ValueError("CPU clock epoch reset/non-monotonic beginnings")
        if previous_end is not None and begin<previous_end:
            raise ValueError("CPU clock went backwards between frames")
        prior=None
        phases=[]
        for ordinal in range(4):
            source=writers[4*index+ordinal]
            if num(source["frame"],"PC frame")!=frame or (
                    num(source["ordinal"],"PC ordinal")!=ordinal+1
                    or source["pc"]!=PCS[ordinal]):
                raise ValueError("writer/clock movie frames not aligned")
            raw_cycle=num(source["cycle"],"absolute writer clock")
            phase=raw_cycle-begin
            if not 0<=phase<=duration:
                raise ValueError("writer outside actual recorded CPU frame")
            phases.append(phase)
            if prior is not None and raw_cycle<=prior:
                raise ValueError("CPU writer within-frame event order reversed")
            prior=raw_cycle
            hexn(source["value"],HEX2,"writer accumulator")
        if phases[1]-phases[0]!=7 or phases[3]-phases[2]!=4:
            raise ValueError("previously observed source CPU pair gaps changed")
        if not EARLY_LOW<=phases[0]<=EARLY_HIGH:
            raise ValueError("first $2005 phase outside observed private range")
        if not LATE_LOW<=phases[2]<=LATE_HIGH:
            raise ValueError("late CPU writer phase outside observed range")
        observed_first.append(phases[0])
        observed_late.append(phases[2])
        previous_begin,previous_end=begin,end
    if len(observed_first)!=321 or len(observed_late)!=321:
        raise ValueError("full private source phase coverage unavailable")
    return {
        **base,
        "frame_boundary_samples":321,
        "source_cpu_frame_phases_checked":1284,
        "published_raw_ppu_ram_anchor_pairs_checked":len(ANCHORS),
        "measured_clock_monotonic_between_frames":True,
        "frame_begin_and_end_from_same_fceux_session":True,
        "source_cpu_writer_phase_within_frame_verified":True,
        "source_rom_fm2_sha256_join_verified":False,
        "ppu_scroll_latch_state_verified":False,
        "effective_ppu_scroll_proven":False,
        "camera_speed_proven":False,
        "road_collision_proven":False,
        "original_image_or_binary_included":False,
    }

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir",required=True,type=Path)
    parser.add_argument("--summary",type=Path)
    options=parser.parse_args()
    summary=validate_clocked_capture(options.private_dir)
    if options.summary:
        repo=Path(__file__).resolve().parents[1]
        dest=options.summary.expanduser().resolve()
        if dest.exists() or dest.is_symlink() or dest==repo or repo in dest.parents:
            raise ValueError("new sanitized summary must be outside source checkout")
        dest.write_text(json.dumps(summary,sort_keys=True,indent=2)+"\n",encoding="utf8")
    print("VPD_PRIVATE_ROAD_PPU321_FRAME_PHASE_PASS"
          " source_frames=321 cpu_writer_phases=1284"
          " frame_begin_clock_source=fceux_registerbefore"
          " original_effective_scroll_proven=no"
          " original_art=no")

if __name__=="__main__":
    main()
