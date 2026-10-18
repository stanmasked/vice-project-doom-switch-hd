#!/usr/bin/env python3
"""Stage141 two-frame sprite-only synthetic Mapper4 native fixtures.

Disable background rendering only for this multi-frame experiment.
All sprite OAM/CHR, palette and MMC3 transition bytes stay unchanged,
so the empty X64 pixel is unambiguously universal backdrop across
both frames instead of depending on background CHR/scroll state.
"""
import argparse
import hashlib
from pathlib import Path

from make_stage137_nine_sprite_rom import make_rom as stage137_make_rom

MODES=("eight_visible","nine_overflow")
BG_AND_SPRITES=bytes((0xA9,0x1E,0x8D,1,0x20))
SPRITES_ONLY=bytes((0xA9,0x14,0x8D,1,0x20))


def make_rom(destination, mode):
    if mode not in MODES:
        raise ValueError("Only two independent Stage141 OAM controls")
    path=Path(destination)
    stage137_make_rom(path,mode)
    original=path.read_bytes()
    if (len(original)!=49168 or original[:16]!=
            b"NES\x1a\x02\x02\x40"+bytes(9) or
            original[16:32784].count(BG_AND_SPRITES)!=4):
        raise ValueError("Stage137 synthetic ROM cannot be mask-isolated")
    isolated=(
        original[:16]+original[16:32784].replace(
            BG_AND_SPRITES,SPRITES_ONLY)+original[32784:])
    if (len(isolated)!=len(original) or
            sum(a!=b for a,b in zip(original,isolated))!=4 or
            isolated[32784:]!=original[32784:]):
        raise ValueError("Unexpected change beyond four PPU MASK immediates")
    path.write_bytes(isolated)
    return hashlib.sha256(isolated).hexdigest()


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output",type=Path)
    cli.add_argument("--mode",choices=MODES,required=True)
    args=cli.parse_args()
    print("STAGE141_SYNTHETIC_SPRITE_ONLY_MULTIFRAME_ROM sha256="+
          make_rom(args.output,args.mode))
