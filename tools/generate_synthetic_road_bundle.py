#!/usr/bin/env python3
"""Write invented 37-slot numeric SD bundle for CI; never use user source.

The seven already-public numeric reference anchors remain unchanged. All
30 other entries are deliberate synthetic constant 66..188 X intervals.
No original-game ROM, movie, RGB screenshot or asset enters the archive.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import struct
import zlib
from audit_private_road_ppu_window import PUBLISHED_IMAGE
from audit_private_legacy_road_geometry import LEGACY_AMBIGUOUS

MAGIC=b"VPDROAD1"
def synthetic_bundle()->bytes:
    samples=[]
    for frame in range(600,921,8):
        if frame in LEGACY_AMBIGUOUS: continue
        left,right=PUBLISHED_IMAGE.get(frame,(66,188))
        samples.append((frame,left,right))
    if len(samples)!=37:
        raise ValueError("synthetic road window has wrong count")
    payload=b"".join(struct.pack("<HBB",*row) for row in samples)
    raw=struct.pack("<8sHHI",MAGIC,1,len(samples),zlib.crc32(payload))+payload
    if len(raw)!=164:raise ValueError("synthetic bundle size invalid")
    return raw

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    # Explicitly write to runner-private NeXium SD, not source checkout.
    root=Path(__file__).resolve().parents[1]
    dest=args.output.expanduser().resolve()
    if dest==root or root in dest.parents:
        raise ValueError("synthetic CI bundle must not enter git checkout")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(synthetic_bundle())
    print("VPD_SYNTHETIC_ROAD_SD_PREPARED bytes=164 samples=37 "
          "nonanchor_observations=invented original_assets=no")

if __name__=="__main__":main()
