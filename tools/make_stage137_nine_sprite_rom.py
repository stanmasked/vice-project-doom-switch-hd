#!/usr/bin/env python3
"""Stage137 private synthetic Mapper4 8/9 OAM sprite and overflow ROMs.

Draw probe at X64. First eight sprites are parked at X160; the ninth
appears at X64 only in the 9-sprite modes. No original game content.
"""
import argparse
import hashlib
from pathlib import Path

from make_stage110_synthetic_midframe_rom import program
from make_stage124_native_quadrant_rom import initialization
from make_stage129_oam_sprite_rom import RENDER_SETUP,MASK_SETUP,SPRITE_Y,explicit_sprite_palette_slot2

MODES=("eight_visible","nine_overflow","ninth_offscreen","nine_8x16")
SPRITE_SETUP=b"\xA9\x18\x8D\x00\x20"
SPRITE16_SETUP=b"\xA9\x38\x8D\x00\x20"
# Force all 256 OAM bytes to $FF before adding eight or nine visible
# sprites. LDX #0, LDA #$FF, STA $2004, INX, BNE -6; 256 iterations.
# Explicitly reset OAMADDR $2003 afterward so OAM0 begins at byte zero.
OAM_CLEAR=(bytes((0xA9,0,0x8D,3,0x20,0xA2,0,0xA9,255,
                  0x8D,4,0x20,0xE8,0xD0,0xFA))+
           bytes((0xA9,0,0x8D,3,0x20)))


def oam_setup(mode):
    if mode not in MODES:
        raise ValueError("Unknown synthetic sprite overflow case")
    out=bytearray(OAM_CLEAR)  # Clear all 64 records, then OAMADDR $00
    nine=mode!="eight_visible"
    entries=9 if nine else 8
    for index in range(entries):
        y=40 if mode=="ninth_offscreen" and index==8 else SPRITE_Y
        x=64 if ((mode=="eight_visible" and index==7) or
                 (nine and index==8)) else 160
        for v in (y,2,0,x):
            out.extend((0xA9,v,0x8D,4,0x20))
    return bytes(out)


def make_rom(path,mode):
    if mode not in MODES:
        raise ValueError("Unexpected nine-sprite test mode")
    base=program()
    if base.count(RENDER_SETUP)!=1 or base.count(MASK_SETUP)!=1:
        raise ValueError("Unexpected base 6502 frame setup")
    payload=base.replace(
        RENDER_SETUP,
        initialization()+oam_setup(mode)+
        # sprite index3 = $2A; use the proven Stage133 slot2 fix too
        # to keep our CHR/palette initialization invariant.
        bytes((0xA9,0x3F,0x8D,6,0x20,0xA9,0x13,0x8D,6,0x20,
               0xA9,0x2A,0x8D,7,0x20))+
        explicit_sprite_palette_slot2()+
        (SPRITE16_SETUP if mode=="nine_8x16" else SPRITE_SETUP),
        1)
    payload=payload.replace(MASK_SETUP,
        bytes((0xA9,0x1E,0x8D,1,0x20)),1)
    if len(payload)>8192:
        raise ValueError("Overflow experiment CPU code out of PRG bank")
    bank=bytearray(b"\xEA"*8192)
    bank[:len(payload)]=payload
    prg=bytearray(bank*4)
    prg[-6:]=b"\x00\xC0"*3
    chr_data=bytearray(16384)
    # Background CHR tile1 intentionally transparent: absent ninth
    # sprite must show universal backdrop palette $0F (XBuf 143).
    chr_data[1024+32:1024+48]=b"\xFF"*16 # sprite tile2 pattern3
    chr_data[1024+48:1024+64]=b"\xFF"*16 # 8x16 lower tile3
    image=b"NES\x1a"+bytes((2,2,0x40,0))+bytes(8)+prg+chr_data
    if len(image)!=49168:
        raise AssertionError("Unexpected iNES Mapper4 size")
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(image)
    return hashlib.sha256(image).hexdigest()


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output",type=Path)
    cli.add_argument("--mode",choices=MODES,required=True)
    args=cli.parse_args()
    print("STAGE137_SYNTHETIC_OAM_OVERFLOW_ROM sha256="+
          make_rom(args.output,args.mode))
