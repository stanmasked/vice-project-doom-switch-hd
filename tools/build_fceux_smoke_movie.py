#!/usr/bin/env python3
"""Create wholly fabricated FM2 for a temporary original-made NES test ROM."""
import argparse
import base64
import hashlib
from pathlib import Path

from build_fceux_smoke_rom import build_rom as build_nrom
from build_fceux_smoke_mmc3_nes2 import build_rom as build_mmc3

MOVIE_FRAMES=64
MAX_SYNTHETIC_FRAMES=4096

def make_movie(rom,frames=MOVIE_FRAMES,pattern="pulse"):
    if type(frames) is not int or not 32<=frames<=MAX_SYNTHETIC_FRAMES:
        raise ValueError('synthetic FM2 frame count must be 32..4096')

    if pattern not in ("pulse","alternating","bursts","idle"):
        raise ValueError("unsupported synthetic input pattern")

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
    def pressed(i):
        if pattern=="pulse": return 12<=i<24
        if pattern=="alternating": return i%2==0
        if pattern=="bursts": return i%257<17
        return False
    rows=["|0|.......A|||" if pressed(i) else "|0|........|||"
          for i in range(frames)]
    return "\n".join(header+rows)+"\n"

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rom",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--frames",type=int,default=MOVIE_FRAMES)
    p.add_argument("--pattern",choices=("pulse","alternating","bursts","idle"),default="pulse")
    a=p.parse_args()
    if a.output.exists() or a.output.is_symlink():
        p.error("refusing to overwrite synthetic movie")
    if not a.output.parent.is_dir():
        p.error("output folder does not exist")
    with a.output.open("x",encoding="ascii") as file:
        file.write(make_movie(a.rom.read_bytes(),frames=a.frames,pattern=a.pattern))
    print(f"SYNTHETIC_FM2_CREATED frames={a.frames} pattern={a.pattern} original_game_proven=no")

if __name__=="__main__":main()
