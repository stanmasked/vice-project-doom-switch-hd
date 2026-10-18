#!/usr/bin/env python3
"""Synthetic Mapper-4 ROM with two distinguishable overlapping OAM sprites.

No original game content; generated ROMs remain outside git.
"""
import argparse
import hashlib
from pathlib import Path
from make_stage110_synthetic_midframe_rom import program
from make_stage124_native_quadrant_rom import initialization
from make_stage129_oam_sprite_rom import RENDER_SETUP, MASK_SETUP, SPRITE_Y, SPRITE_X

SPRITE_PALETTE0_COLOR = 0x2A
SPRITE_PALETTE1_COLOR = 0x38
MODES = ("first_front", "palette_swapped", "first_transparent",
         "first_behind", "first_behind_clear")


def dual_oam_init(mode, *, second_opaque=True):
    if mode not in MODES or type(second_opaque) is not bool:
        raise ValueError("Unsupported two-OAM sprite fixture")
    output = bytearray((0xA9, 0x3F, 0x8D, 6, 0x20,
                        0xA9, 0x11, 0x8D, 6, 0x20))
    for color in (0x1A, 0x2B, SPRITE_PALETTE0_COLOR):
        output.extend((0xA9, color, 0x8D, 7, 0x20))
    output.extend((0xA9, 0x3F, 0x8D, 6, 0x20,
                   0xA9, 0x15, 0x8D, 6, 0x20))
    for color in (0x1B, 0x2C, SPRITE_PALETTE1_COLOR):
        output.extend((0xA9, color, 0x8D, 7, 0x20))
    output.extend((0xA9, 0, 0x8D, 3, 0x20))
    first_tile = 3 if mode == "first_transparent" else 2
    first_attr = (1 if mode == "palette_swapped" else
                  0x20 if mode in ("first_behind", "first_behind_clear") else 0)
    second_attr = 0 if mode == "palette_swapped" else 1
    second_tile = 2 if second_opaque else 3
    for value in (SPRITE_Y, first_tile, first_attr, SPRITE_X,
                  SPRITE_Y, second_tile, second_attr, SPRITE_X):
        output.extend((0xA9, value, 0x8D, 4, 0x20))
    return bytes(output)


def make_rom(destination, mode, *, second_opaque=True):
    if mode not in MODES or type(second_opaque) is not bool:
        raise ValueError("Invalid two-sprite ROM control")
    base = program()
    if base.count(RENDER_SETUP) != 1 or base.count(MASK_SETUP) != 1:
        raise ValueError("Pinned synthetic render setup changed")
    body = base.replace(
        RENDER_SETUP,
        initialization() + dual_oam_init(mode, second_opaque=second_opaque) +
        bytes((0xA9, 0x18, 0x8D, 0, 0x20)), 1)
    body = body.replace(MASK_SETUP, bytes((0xA9, 0x1E, 0x8D, 1, 0x20)), 1)
    if len(body) > 8192:
        raise ValueError("Generated two-sprite code exceeds PRG bank")
    bank = bytearray(b"\xEA" * 8192)
    bank[:len(body)] = body
    prg = bytearray(bank * 4)
    prg[-6:] = b"\x00\xC0" * 3
    chr_data = bytearray(16384)
    if mode != "first_behind_clear":
        chr_data[1024+16:1024+32] = b"\xFF" * 16
    chr_data[1024+32:1024+48] = b"\xFF" * 16
    rom = b"NES\x1a" + bytes((2, 2, 0x40, 0)) + bytes(8) + prg + chr_data
    if len(rom) != 49168:
        raise AssertionError("iNES Mapper-4 byte length changed")
    p = Path(destination)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(rom)
    return hashlib.sha256(rom).hexdigest()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("destination", type=Path)
    cli.add_argument("--mode", required=True, choices=MODES)
    cli.add_argument("--transparent-second", action="store_true")
    args = cli.parse_args()
    print("STAGE131_SYNTHETIC_DUAL_OAM_ROM sha256=" +
          make_rom(args.destination, args.mode,
                   second_opaque=not args.transparent_second))
