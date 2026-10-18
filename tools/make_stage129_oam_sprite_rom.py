#!/usr/bin/env python3
"""Stage129 independent Mapper-4 OAM sprite vs BG pattern collision ROM.

Only synthetic contents, generated to transient native CI folders.
The sprite and BG use different controlled CHR tile IDs in bank1.
"""
import argparse
import hashlib
from pathlib import Path

from make_stage110_synthetic_midframe_rom import program
from make_stage124_native_quadrant_rom import initialization

RENDER_SETUP = bytes((0xA9, 0x10, 0x8D, 0, 0x20))
MASK_SETUP = bytes((0xA9, 0x0A, 0x8D, 1, 0x20))
SPRITE_Y = 120
SPRITE_X = 64
SPRITE_TILE_OPAQUE = 2
SPRITE_TILE_TRANSPARENT = 3
SPRITE_COLOR = 0x2A


def sprite_initialization(*, behind=False, sprite_opaque=True,
                          hflip=False, vflip=False):
    if any(type(v) is not bool for v in (behind,sprite_opaque,hflip,vflip)):
        raise ValueError("Sprite flags must be actual booleans")
    # Set sprite palette bytes at $3F11..$3F13; do not touch
    # the universal backdrop slot $3F10.
    stream = bytearray((0xA9, 0x3F, 0x8D, 6, 0x20,
                        0xA9, 0x11, 0x8D, 6, 0x20))
    for color in (0x1A, 0x2B, SPRITE_COLOR):
        stream.extend((0xA9, color, 0x8D, 7, 0x20))
    # OAM sprite 0 only: [Y, tile index, attributes, X].
    stream.extend((0xA9, 0, 0x8D, 3, 0x20))
    for value in (SPRITE_Y, SPRITE_TILE_OPAQUE if sprite_opaque
                  else SPRITE_TILE_TRANSPARENT,
                  (0x20 if behind else 0) | (0x40 if hflip else 0) |
                  (0x80 if vflip else 0), SPRITE_X):
        stream.extend((0xA9, value, 0x8D, 4, 0x20))
    return bytes(stream)


def explicit_sprite_palette_slot2():
    """Stage133-only direct PPUADDR/PPUDATA write to $3F12.

    The native Stage133 diagnostic observed $01 from sprite slot2
    instead of the sequentially initialized $2B. This additional
    address-bound write is a targeted test of PPU palette state; it
    preserves the other 15 sprite/BG slots and all original synthetic
    stage129/131 ROMs.
    """
    return bytes((0xA9, 0x3F, 0x8D, 6, 0x20,
                  0xA9, 0x12, 0x8D, 6, 0x20,
                  0xA9, 0x2B, 0x8D, 7, 0x20,
                  # Restore PPU VRAM and scroll latch after direct
                  # palette access; do not start drawing at $3F13.
                  0xA9, 0x20, 0x8D, 6, 0x20,
                  0xA9, 0x00, 0x8D, 6, 0x20,
                  0xA9, 0x00, 0x8D, 5, 0x20, 0x8D, 5, 0x20))


def asymmetric_pattern(row, column):
    if (type(row) is not int or not 0 <= row < 8 or
            type(column) is not int or not 0 <= column < 8):
        raise ValueError("Asymmetric CHR coordinates must be 0..7")
    return 1 + ((2 * row + column) % 3)


def make_rom(destination, *, bg_opaque=True, sprite_opaque=True,
             behind=False, sprite_enabled=True, hflip=False,
             vflip=False, asymmetric_sprite=False):
    if any(type(v) is not bool for v in
           (bg_opaque, sprite_opaque, behind, sprite_enabled,
            hflip, vflip, asymmetric_sprite)):
        raise ValueError("Sprite compositor controls must be booleans")
    base = program()
    if base.count(RENDER_SETUP) != 1 or base.count(MASK_SETUP) != 1:
        raise ValueError("Pinned synthetic 6502 PPU setup changed")
    # Preserve CPU timing within all four variants, except the single
    # byte sprite priority flag or the distinct CHR tile occupancy.
    payload = base.replace(
        RENDER_SETUP, initialization() +
        sprite_initialization(behind=behind, sprite_opaque=sprite_opaque,
                              hflip=hflip, vflip=vflip) +
        (explicit_sprite_palette_slot2() if asymmetric_sprite else b"") +
        bytes((0xA9, 0x18, 0x8D, 0, 0x20)), 1)
    payload = payload.replace(
        MASK_SETUP,
        bytes((0xA9, 0x1E if sprite_enabled else 0x0E, 0x8D, 1, 0x20)),
        1)
    if len(payload) > 8192:
        raise ValueError("Generated OAM program exceeds PRG bank")
    bank = bytearray(b"\xEA" * 8192)
    bank[:len(payload)] = payload
    prg = bytearray(bank * 4)
    prg[-6:] = b"\x00\xC0" * 3
    chr_data = bytearray(16384)
    if bg_opaque:
        chr_data[1024 + 16:1024 + 32] = b"\xFF" * 16
    # Sprite tile2 is independently solid in both pattern planes.
    if asymmetric_sprite:
        # Every sprite pixel stays nonzero, while X/Y patterns vary.
        for row in range(8):
            low=0
            high=0
            for col in range(8):
                bit=7-col
                pat=asymmetric_pattern(row,col)
                low |= (pat & 1) << bit
                high |= ((pat >> 1) & 1) << bit
            chr_data[1024+32+row]=low
            chr_data[1024+40+row]=high
    else:
        chr_data[1024 + 32:1024 + 48] = b"\xFF" * 16
    # Tile3 is always blank for the transparent-sprite negative case.
    output = b"NES\x1a" + bytes((2, 2, 0x40, 0)) + bytes(8) + prg + chr_data
    if len(output) != 49168:
        raise AssertionError("Synthetic mapper4 image size changed")
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(output)
    return hashlib.sha256(output).hexdigest()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("destination", type=Path)
    cli.add_argument("--background-transparent", action="store_true")
    cli.add_argument("--sprite-transparent", action="store_true")
    cli.add_argument("--sprite-behind", action="store_true")
    cli.add_argument("--sprite-disabled", action="store_true")
    args = cli.parse_args()
    print("STAGE129_SYNTHETIC_OAM_SPRITE_ROM sha256=" +
          make_rom(args.destination,
                   bg_opaque=not args.background_transparent,
                   sprite_opaque=not args.sprite_transparent,
                   behind=args.sprite_behind,
                   sprite_enabled=not args.sprite_disabled))
