#!/usr/bin/env python3
"""Stage138 synthetic Mapper4 moving ninth-OAM sprite 8x16 fixtures.

Prepare temporally separated upper and lower scanline OAM membership.
Source/model ROM proof only: no FCEUX raster claim until native witness.
"""
import argparse
import hashlib
from pathlib import Path

from make_stage110_synthetic_midframe_rom import program
from make_stage124_native_quadrant_rom import initialization
from make_stage129_oam_sprite_rom import (
    RENDER_SETUP, MASK_SETUP, explicit_sprite_palette_slot2)
from make_stage137_nine_sprite_rom import OAM_CLEAR, SPRITE16_SETUP
from audit_stage136_oam_eight_limit import sprite_scanline_model

MODES=("eight_stable","nine_late","seven_plus_late","nine_early")
UPPER_ROW=124
LOWER_ROW=132


def slots(mode):
    if mode not in MODES:
        raise ValueError("Unknown timed nine-OAM control")
    y=[120]*8 + [255]
    if mode in ("nine_late","seven_plus_late"):
        y[8]=128
    if mode=="nine_early":
        y[8]=120
    if mode=="seven_plus_late":
        y[7]=255
    return tuple(y+[255]*55)


def expected(mode):
    source=slots(mode)
    upper=sprite_scanline_model(source,UPPER_ROW,height=16)
    lower=sprite_scanline_model(source,LOWER_ROW,height=16)
    # Raster X64 hosts only original OAM8. When OAM8 is selected it
    # is drawn (palette3=$2A -> XBuf170); otherwise universal backdrop.
    xbuf_upper=170 if 8 in upper["chosen_oam_indexes"] else 143
    xbuf_lower=170 if 8 in lower["chosen_oam_indexes"] else 143
    return {"upper":upper,"lower":lower,
            "xbuf_upper":xbuf_upper,"xbuf_lower":xbuf_lower}


def oam_setup(mode):
    ys=slots(mode)[:9]
    output=bytearray(OAM_CLEAR)
    for i,y in enumerate(ys):
        x=64 if i==8 else 160
        for value in (y,2,0,x):
            output.extend((0xA9,value,0x8D,4,0x20))
    return bytes(output)


def make_rom(destination,mode):
    if mode not in MODES:
        raise ValueError("Unexpected Stage138 sprite membership mode")
    base=program()
    if base.count(RENDER_SETUP)!=1 or base.count(MASK_SETUP)!=1:
        raise ValueError("Pinned synthetic raster anchors changed")
    init=(initialization()+oam_setup(mode)+
          bytes((0xA9,0x3F,0x8D,6,0x20,
                 0xA9,0x13,0x8D,6,0x20,
                 0xA9,0x2A,0x8D,7,0x20))+
          explicit_sprite_palette_slot2()+SPRITE16_SETUP)
    payload=base.replace(RENDER_SETUP,init,1).replace(
        MASK_SETUP,bytes((0xA9,0x1E,0x8D,1,0x20)),1)
    if len(payload)>8192:
        raise ValueError("Stage138 CPU program exceeds 8KiB bank")
    bank=bytearray(b"\xEA"*8192)
    bank[:len(payload)]=payload
    prg=bytearray(bank*4)
    prg[-6:]=b"\x00\xC0"*3
    chr_data=bytearray(16384)
    # Background zero, sprite both tile2 and tile3 pattern3.
    chr_data[1024+32:1024+64]=b"\xFF"*32
    image=b"NES\x1a"+bytes((2,2,0x40,0))+bytes(8)+prg+chr_data
    if len(image)!=49168:
        raise AssertionError("Stage138 iNES size changed")
    dest=Path(destination)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(image)
    return hashlib.sha256(image).hexdigest()


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output",type=Path)
    cli.add_argument("--mode",choices=MODES,required=True)
    args=cli.parse_args()
    print("STAGE138_SYNTHETIC_OAM_TEMPORAL_ROM sha256="+
          make_rom(args.output,args.mode))
