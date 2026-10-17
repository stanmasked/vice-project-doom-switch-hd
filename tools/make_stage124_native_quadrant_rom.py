#!/usr/bin/env python3
"""Stage124 standalone Mapper-4 ROM with four actual PPU attribute palettes.

Private CI generated ROM only; no game assets, screenshots or CHR dumps in git.
CPU program waits for VBlank and selects the filled MMC3 CHR bank during raster.
"""
import argparse
import hashlib
from pathlib import Path

from audit_stage123_quadrant_palette import ATTRIBUTE_BYTE, PALETTE_RAM
from make_stage110_synthetic_midframe_rom import program

RENDER_SETUP = bytes((0xA9, 0x10, 0x8D, 0, 0x20))
PAGE_HIGHS = (0x23, 0x27, 0x2B, 0x2F)
# 256 writes; branch -6 from BNE's following PC to the STA.
TILE_PAGE = bytes((0xA2, 0, 0xA9, 1, 0x8D, 7, 0x20, 0xE8, 0xD0, 0xFA))
# After setting $2006 to attribute area, write 64 copies of one byte.
# Branch -8 returns to the STA, not to the LDA immediate.
ATTR_LOOP_SUFFIX = bytes((0x8D, 7, 0x20, 0xE8, 0xE0, 0x40, 0xD0, 0xF8))


def initialization(attribute=ATTRIBUTE_BYTE, distinct_palette=True, targeted_quadrant=None):
    if type(attribute) is not int or not 0 <= attribute <= 255:
        raise ValueError("Attribute byte must be an unsigned byte")
    if type(distinct_palette) is not bool:
        raise ValueError("Palette control must be a boolean")
    if targeted_quadrant is not None and (
            type(targeted_quadrant) is not int or
            targeted_quadrant not in range(4) or
            attribute != ATTRIBUTE_BYTE or not distinct_palette):
        raise ValueError("Selective color mutation needs E4 and distinct palette")
    stream = bytearray((0xA9, 0x20, 0x8D, 6, 0x20, 0xA9, 0,
                        0x8D, 6, 0x20))
    stream.extend(TILE_PAGE * 16)
    for page in PAGE_HIGHS:
        # $23C0/$27C0/$2BC0/$2FC0: 64 attribute bytes per page.
        stream.extend((0xA9, page, 0x8D, 6, 0x20,
                       0xA9, 0xC0, 0x8D, 6, 0x20,
                       0xA2, 0, 0xA9, attribute))
        stream.extend(ATTR_LOOP_SUFFIX)
    stream.extend((0xA9, 0x3F, 0x8D, 6, 0x20, 0xA9, 0, 0x8D, 6, 0x20))
    palette = PALETTE_RAM if distinct_palette else (
        0x0F, 0x16, 0x27, 0x30,
        0x0F, 0x11, 0x21, 0x30,
        0x0F, 0x12, 0x22, 0x30,
        0x0F, 0x13, 0x23, 0x30)
    palette = list(palette)
    if targeted_quadrant is not None:
        # One and only one background palette entry changes. CHR, source
        # nametable, all $E4 attributes and the other 15 colors stay fixed.
        palette[3+4*targeted_quadrant] = 0x34+targeted_quadrant
    for color in palette:
        stream.extend((0xA9, color, 0x8D, 7, 0x20))
    # Restore first nametable address and horizontal/vertical scroll latches.
    stream.extend((0xA9, 0x20, 0x8D, 6, 0x20, 0xA9, 0, 0x8D, 6, 0x20,
                   0xA9, 0, 0x8D, 5, 0x20, 0x8D, 5, 0x20))
    return bytes(stream)


def make_rom(dest, *, attribute=ATTRIBUTE_BYTE, distinct_palette=True,
             switch=True, targeted_quadrant=None):
    if type(switch) is not bool:
        raise ValueError("Bank-switch control must be a boolean")
    base = program(switch=switch)
    if base.count(RENDER_SETUP) != 1:
        raise ValueError("Pinned synthetic 6502 raster setup not found exactly once")
    if targeted_quadrant is not None and not switch:
        raise ValueError("Selective mutation requires active CHR bank change")
    patched = base.replace(
        RENDER_SETUP,
        initialization(attribute, distinct_palette, targeted_quadrant)
        + RENDER_SETUP, 1)
    if len(patched) > 8192:
        raise ValueError("Synthetic program exceeds the 8 KiB PRG bank")
    prg_bank = bytearray(b"\xEA" * 8192)
    prg_bank[:len(patched)] = patched
    prg = bytearray(prg_bank * 4)
    prg[-6:] = b"\x00\xC0" * 3
    chr_data = bytearray(16384)
    # Only mapper-4 CHR bank1 (selected after VBlank) has solid pixels.
    # Tile1=filled on all 8 rows, both low/high bitplanes -> pattern3.
    chr_data[1024 + 16:1024 + 32] = b"\xFF" * 16
    result = b"NES\x1a" + bytes((2, 2, 0x40, 0)) + bytes(8) + prg + chr_data
    if len(result) != 49168:
        raise AssertionError("iNES ROM length invariant violated")
    path = Path(dest)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(result)
    return hashlib.sha256(result).hexdigest()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("destination", type=Path)
    cli.add_argument("--zero-attributes", action="store_true")
    cli.add_argument("--uniform-palette", action="store_true")
    cli.add_argument("--fixed-chr", action="store_true")
    cli.add_argument("--targeted-quadrant", type=int, default=None)
    args = cli.parse_args()
    print("STAGE124_SYNTHETIC_QUADRANT_ROM sha256=" +
          make_rom(args.destination, attribute=0 if args.zero_attributes else ATTRIBUTE_BYTE,
                   distinct_palette=not args.uniform_palette,
                   switch=not args.fixed_chr,
                   targeted_quadrant=args.targeted_quadrant))
