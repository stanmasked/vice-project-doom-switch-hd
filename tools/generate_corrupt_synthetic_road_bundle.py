#!/usr/bin/env python3
"""Create deliberately broken source-FREE numeric bundles, outside Git.

Variants:
  bad_crc     original-free generated payload flipped without updating CRC
  bad_anchor  first public numeric anchor changed, CRC recomputed
  truncated   missing one byte from entirely synthetic 164-byte packet
"""
from __future__ import annotations
import argparse
from pathlib import Path
import struct
import zlib
from generate_synthetic_road_bundle import synthetic_bundle

KINDS=("bad_crc","bad_anchor","truncated")
def corrupt(kind:str)->bytes:
    original=bytearray(synthetic_bundle())
    if kind=="bad_crc":
        original[-1]^=1
    elif kind=="bad_anchor":
        original[18]=67  # first documented frame 600 left=66
        struct.pack_into("<I",original,12,zlib.crc32(original[16:]))
    elif kind=="truncated":
        original.pop()
    else:
        raise ValueError("unsupported safe synthetic corruption variant")
    result=bytes(original)
    if result==synthetic_bundle():raise ValueError("corruption had no effect")
    return result

def main()->None:
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--kind",required=True,choices=KINDS)
    cli.add_argument("--output",required=True,type=Path)
    args=cli.parse_args()
    root=Path(__file__).resolve().parents[1]
    dest=args.output.expanduser().resolve()
    if dest==root or root in dest.parents:
        raise ValueError("never write even synthetic data inside public checkout")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(corrupt(args.kind))
    print("VPD_SYNTHETIC_CORRUPT_ROAD_SD_PREPARED"
          f" variant={args.kind} original_art=no")
if __name__=="__main__":main()
