#!/usr/bin/env python3
"""Audit private same-session 41-slot FCEUX road RGB scanline capture.

This reads owner-private RGB pixels only. Never print, publish, return,
or cache the actual pixel values. Old 37/4 ROI classification is NOT
established by counting the scanline bytes. No original collision map,
camera velocity, or effective PPU scrolling may be inferred.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import struct

MAGIC=b"VPDRGB41"
SCHEMA=struct.Struct("<8sHHHH4B")   # magic,slots,width,rows,reserved,y[]
SLOT_FRAMES=tuple(range(600,921,8))
SCANLINES=(120,140,160,180)
WIDTH=256
BYTES_PER_PIXEL=3
RECORD_SIZE=2+WIDTH*len(SCANLINES)*BYTES_PER_PIXEL
EXACT_SIZE=SCHEMA.size+len(SLOT_FRAMES)*RECORD_SIZE

def validate_scanlines(path:Path)->dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size!=EXACT_SIZE:
        raise ValueError("private original RGB scanline file missing or wrong size")
    with path.open("rb") as stream:
        header=stream.read(SCHEMA.size)
        magic,count,width,rows,reserved,*ys=SCHEMA.unpack(header)
        if (magic,count,width,rows,reserved,tuple(ys))!=(
                MAGIC,len(SLOT_FRAMES),WIDTH,len(SCANLINES),0,SCANLINES):
            raise ValueError("source RGB format/scanline contract mismatch")
        for frame in SLOT_FRAMES:
            n=stream.read(2)
            if len(n)!=2 or struct.unpack("<H",n)[0]!=frame:
                raise ValueError("missing/duplicated/reordered source RGB frame")
            pixels=stream.read(RECORD_SIZE-2)
            if len(pixels)!=RECORD_SIZE-2:
                raise ValueError("truncated original RGB scanlines")
        if stream.read(1):
            raise ValueError("unexpected extra source-image bytes")
    return {
        "source_image_capture_slots":41,
        "source_image_capture_start":600,
        "source_image_capture_stop":920,
        "source_image_capture_interval":8,
        "source_image_scanlines_per_slot":4,
        "source_image_rgb_triplets":41*4*256,
        "new_rgb_samples_same_fceux_session_as_ppu":True,
        "previous_legacy_37_of_41_edge_classification_reproduced":False,
        "legacy_report_rom_fm2_sha256_join_verified":False,
        "original_camera_speed_proven":False,
        "original_ppu_effective_scroll_proven":False,
        "original_source_pixels_in_summary":False,
    }

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-dir",required=True,type=Path)
    opts=p.parse_args()
    validate_scanlines(opts.private_dir/"road_321_rgb_scanlines.bin")
    print("VPD_PRIVATE_ROAD_RGB_SAME_SESSION_PASS"
          " slots=41 scanned_rows=4 rgb_triplets=41984"
          " original_rgb_output_disclosed=no"
          " legacy_37_4_segmentation_proven=no")
if __name__=="__main__":main()
