#!/usr/bin/env python3
"""Private exact-RGB road-gray remeasurement from the SAME FCEUX session.

Requires a fresh 41-frame RGB capture cryptographically sealed to the
321-frame PPU source session. The old numeric report has no SHA-256
and cannot be retroactively authenticated. Fail unless all 41 source
frame statuses and exact accepted median X coordinates reproduce it.

Never print or publish the actual FCEUX image pixels, source image-space
edges beyond previously published examples, ROM/FM2 hashes or paths.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
import struct

from audit_private_road_rgb_321 import (
    validate_scanlines,SCHEMA,SLOT_FRAMES,SCANLINES,WIDTH,RECORD_SIZE
)
from audit_private_legacy_road_geometry import (
    LEGACY_AMBIGUOUS,validate_legacy_report
)
from audit_private_road_ppu_window import PUBLISHED_IMAGE
from seal_private_road_ppu_321 import verify as verify_same_source

ROAD_GRAY=bytes((117,117,117))
MIN_WIDTH,MAX_WIDTH=30,200
SCANLINE_COUNT_REQUIRED=3

def row_span(payload:bytes)->tuple[int,int]|None:
    if len(payload)!=WIDTH*3:
        raise ValueError("private image row does not contain 256 RGB pixels")
    mask=[x for x in range(WIDTH)
          if payload[3*x:3*x+3]==ROAD_GRAY]
    if len(mask)<MIN_WIDTH:
        return None
    left,right=mask[0],mask[-1]
    if not MIN_WIDTH<=right-left+1<=MAX_WIDTH:
        return None
    return left,right

def extract_report(image:Path)->list[dict]:
    validate_scanlines(image)
    records=[]
    with image.open("rb") as stream:
        stream.seek(SCHEMA.size)
        for frame in SLOT_FRAMES:
            movie_frame=struct.unpack("<H",stream.read(2))[0]
            if movie_frame!=frame:
                raise ValueError("road image/PPU source movie frames misaligned")
            segments=[]
            for y in SCANLINES:
                span=row_span(stream.read(WIDTH*3))
                if span is not None:
                    segments.append(span)
            n=len(segments)
            if n<SCANLINE_COUNT_REQUIRED:
                records.append({"frame":frame,"roi_valid":False,
                                "valid_scanline_count":n})
                continue
            left=int(median([a for a,b in segments]))
            right=int(median([b for a,b in segments]))
            if left>right or not MIN_WIDTH<=right-left+1<=MAX_WIDTH:
                raise ValueError("median RGB road segment outside ROI bounds")
            records.append({
                "frame":frame,"roi_valid":True,
                "observed_left_edge":left,
                "observed_right_edge":right,
                "observed_width":right-left+1,
                "observed_center_x":(left+right)/2,
                "valid_scanline_count":n
            })
    return records

def compare_to_legacy(records:list[dict],legacy:dict)->dict:
    validate_legacy_report(legacy)
    if len(records)!=41:
        raise ValueError("incomplete newly captured road RGB samples")
    expected_frames=list(SLOT_FRAMES)
    if [row["frame"] for row in records]!=expected_frames:
        raise ValueError("new RGB road timeline differs from movie")
    accepted=[r for r in records if r["roi_valid"]]
    ambiguous=[r["frame"] for r in records if not r["roi_valid"]]
    if len(accepted)!=37 or set(ambiguous)!=LEGACY_AMBIGUOUS:
        raise ValueError("new same-session RGB cannot reproduce 37/4 pattern")
    for row in accepted:
        anchor=PUBLISHED_IMAGE.get(row["frame"])
        if anchor and (row["observed_left_edge"],row["observed_right_edge"])!=anchor:
            raise ValueError("original published RGB interval not reproduced")
    for fresh,old in zip(records,legacy["frames"]):
        if fresh!=old:
            raise ValueError("fresh same-session road color segmentation "
                             "does not reproduce the hashless legacy report")
    return {
        "new_same_session_original_rgb_slots_compared":41,
        "new_original_rgb_intervals_reproduced":37,
        "source_gray_scanline_rows_tested":164,
        "ambiguous_source_slots_preserved":4,
        "published_original_image_anchors_checked":len(PUBLISHED_IMAGE),
        "fresh_same_session_rgb_and_ppu_evidence_available":True,
        "full_road_color_numeric_values_in_output":False,
        "old_hashless_road_report_sha256_proven":False,
        "effective_ppu_scroll_proven":False,
        "source_camera_speed_proven":False,
        "physical_collision_geometry_proven":False,
    }

def audit(rom:Path,movie:Path,folder:Path,legacy_path:Path)->dict:
    # Verify actual ROM, movie and RGB/CPU clock/PPU artifacts first.
    identity=verify_same_source(rom,movie,folder)
    if not identity.get("same_fceux_session_41_rgb_slots_and_321_ppu_frames_sealed"):
        raise ValueError("unsealed or wrong-session source road RGB")
    if legacy_path.is_symlink() or not legacy_path.is_file():
        raise ValueError("private legacy road report unavailable or linked")
    report=json.loads(legacy_path.read_text("utf8"))
    summary=compare_to_legacy(
        extract_report(folder/"road_321_rgb_scanlines.bin"),report)
    return {**summary,"same_original_rom_fm2_rgb_ppu_source_seal":True}

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rom",type=Path,required=True)
    p.add_argument("--movie",type=Path,required=True)
    p.add_argument("--private-dir",type=Path,required=True)
    p.add_argument("--legacy-numeric-report",type=Path,required=True)
    a=p.parse_args()
    audit(a.rom,a.movie,a.private_dir,a.legacy_numeric_report)
    print("VPD_PRIVATE_SAME_SESSION_ROAD_RGB_REPRODUCTION_PASS"
          " source_rgb_slots=41 road_intervals_reproduced=37"
          " ambiguous_slots=4 old_road_hash_identity_proven=no"
          " original_collision_camera_proven=no")

if __name__=="__main__":
    main()
