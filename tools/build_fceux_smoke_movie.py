#!/usr/bin/env python3
"""Create wholly fabricated FM2 for a temporary original-made NES test ROM."""
import argparse
import base64
import hashlib
from pathlib import Path

MOVIE_FRAMES=64

def make_movie(rom):
    if len(rom)!=16+32768+8192 or rom[:8]!=b"NES\x1a"+bytes([2,1,0,0]):
        raise ValueError("not the synthetic NROM fixture")
    digest=base64.b64encode(hashlib.md5(rom[16:]).digest()).decode("ascii")
    header=[
        "version 3","emuVersion 26500","rerecordCount 0","palFlag 0",
        "romFilename fceux_fabricated",
        "romChecksum base64:"+digest,
        "guid C9E78513-DB6A-4D28-9B16-7AB3F60BA348",
        "fourscore 0","port0 1","port1 0","port2 0","FDS 0","NewPPU 0"
    ]
    rows=["|0|.......A|||" if 12<=i<24 else "|0|........|||"
          for i in range(MOVIE_FRAMES)]
    return "\n".join(header+rows)+"\n"

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rom",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.output.is_symlink():
        p.error("refusing to overwrite synthetic movie")
    if not a.output.parent.is_dir():
        p.error("output folder does not exist")
    with a.output.open("x",encoding="ascii") as file:
        file.write(make_movie(a.rom.read_bytes()))
    print("SYNTHETIC_FM2_CREATED frames=64 original_game_proven=no")

if __name__=="__main__":main()
