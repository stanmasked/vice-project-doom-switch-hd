#!/usr/bin/env python3
"""Create wholly fabricated FM2 for a temporary original-made NES test ROM."""
import argparse
import base64
import hashlib
from pathlib import Path

from build_fceux_smoke_rom import build_rom as build_nrom
from build_fceux_smoke_mmc3_nes2 import build_rom as build_mmc3

MOVIE_FRAMES=64

def make_movie(rom):
    # Whitelist exact handcrafted ROM bytes. Never generate a public-runner
    # FM2 from an arbitrary external/commercial ROM merely because its
    # iNES header happens to have the correct dimensions.
    if rom!=build_nrom() and rom!=build_mmc3():
        raise ValueError("not an exact wholly synthetic ROM fixture")
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
