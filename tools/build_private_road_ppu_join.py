#!/usr/bin/env python3
"""Build and audit an owner-private SAME-session 41/321 road/PPU join.

All 41 original RGB source slots, 37 accepted road image-space edges
and 321 CPU writer / frame-relative PPU $2005 records derive from
one SHA-256 sealed ROM/FM2 FCEUX session. Raw derived documents
exist in memory only. Never publish JSON with unpublished source X
positions, raw CPU cycles, ROM/FM2 hashes or original RGB pixels.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from audit_private_road_mask_reproduction import (
    audit as verify_reproduction,extract_report
)
from audit_private_road_ppu_window import validate_complete_window
from audit_private_road_ppu_321_trace import (
    rows, W_FIELDS,R_FIELDS,PCS,hexn,HEX2,num,START,STOP
)
from audit_private_road_ppu_321_frame_phase import CLOCK_FIELDS
from seal_private_road_ppu_321 import PRE,PRE_FIELDS,_json

def derive_documents(folder:Path)->tuple[dict,dict]:
    """Private ephemeral docs. Do not log or serialize returned content."""
    locked=_json(folder/PRE,PRE_FIELDS)
    headers={
        "rom_sha256":locked["rom_sha256"],
        "fm2_sha256":locked["fm2_sha256"],
        "movie_frame_origin":"zero_based_FM2",
    }
    road={"schema":"road_image_cross_sections_window_v1",
          **headers,"slots":[]}
    private_slots=extract_report(folder/"road_321_rgb_scanlines.bin")
    for entry in private_slots:
        frame=entry["frame"]
        if entry["roi_valid"]:
            road["slots"].append({
                "frame":frame,"status":"accepted",
                "left":entry["observed_left_edge"],
                "right":entry["observed_right_edge"],
            })
        else:
            road["slots"].append({"frame":frame,"status":"ambiguous"})
    writers=rows(folder/"road_321_writers.tsv",W_FIELDS,321*4)
    rams=rows(folder/"road_321_postframe.tsv",R_FIELDS,321)
    clocks=rows(folder/"road_321_frame_clock.tsv",CLOCK_FIELDS,321)
    ppu={"schema":"ppu_cpu_writer_phases_v1",
         **headers,"samples":[]}
    for index,frame in enumerate(range(START,STOP+1)):
        clock=clocks[index]
        ram=rams[index]
        if (num(clock["frame"],"clock frame")!=frame or
            num(ram["frame"],"RAM frame")!=frame):
            raise ValueError("private PPU source and RGB frame indices differ")
        begin=num(clock["begin_cycle"],"frame source clock")
        values=[]
        phases=[]
        for i in range(4):
            r=writers[index*4+i]
            if (num(r["frame"],"writer frame")!=frame or
                num(r["ordinal"],"writer ordinal")!=i+1 or
                r["pc"]!=PCS[i]):
                raise ValueError("source CPU PC sequence differs from movie")
            values.append(hexn(r["value"],HEX2,"actual $2005 write"))
            phases.append(num(r["cycle"],"CPU clock")-begin)
        ppu["samples"].append({
            "frame":frame,
            "writer_pcs":list(PCS),
            "written_values":values,
            "cpu_cycles_after_previous_frame":phases,
            "ram_0d_postframe":hexn(ram["ram_0d"],HEX2,"source RAM $0D")
        })
    return road,ppu

def audit(rom:Path,movie:Path,capture:Path,legacy:Path)->dict:
    # Cryptographic original full input/outputs and fresh 37/4 RGB
    # reproduction MUST pass before any join can be claimed.
    reproduced=verify_reproduction(rom,movie,capture,legacy)
    if not (reproduced["same_original_rom_fm2_rgb_ppu_source_seal"] and
            reproduced["new_original_rgb_intervals_reproduced"]==37):
        raise ValueError("original same-session source provenance incomplete")
    road,ppu=derive_documents(capture)
    result=validate_complete_window(road,ppu)
    if (result["cpu_frames_checked"]!=321 or
        result["road_cross_sections_accepted"]!=37 or
        result["source_ppu_writes_checked"]!=1284):
        raise ValueError("complete original source window join insufficient")
    return {
        "original_same_session_ppu_rgb_numeric_join_checked":True,
        "new_source_road_image_slots":41,
        "new_source_accepted_road_intervals":37,
        "new_source_ambiguous_road_intervals":4,
        "new_source_cpu_movie_frames":321,
        "new_source_cpu_writer_events":1284,
        "original_anchor_road_ppu_pairs_checked":4,
        "same_full_file_rom_fm2_sha256_in_both_ephemeral_docs":True,
        "legacy_hashless_numeric_report_sha256_authenticated":False,
        "original_nes_ppu_effective_scroll_proven":False,
        "original_road_physics_collision_proven":False,
        "original_game_camera_speed_proven":False,
        "unpublished_source_numeric_or_rgb_in_result":False,
    }

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rom",required=True,type=Path)
    p.add_argument("--movie",required=True,type=Path)
    p.add_argument("--private-dir",required=True,type=Path)
    p.add_argument("--legacy-numeric-report",required=True,type=Path)
    opts=p.parse_args()
    # No output files are created: RAM-only source docs, sanitized result.
    audit(opts.rom,opts.movie,opts.private_dir,opts.legacy_numeric_report)
    print("VPD_PRIVATE_ORIGINAL_ROAD_PPU321_JOIN_PASS"
          " original_rgb_slots=41 accepted=37 ambiguous=4"
          " original_ppu_cpu_frames=321 original_cpu_writes=1284"
          " same_sealed_rom_fm2_source=yes"
          " effective_ppu_scroll_proven=no"
          " original_camera_collision_proven=no"
          " source_values_disclosed=no")

if __name__=="__main__":main()
