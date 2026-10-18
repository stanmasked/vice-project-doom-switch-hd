#!/usr/bin/env python3
"""Stage134 generated Mapper-4 8x16 two-tile OAM sprite fixtures.

Four controls exercise tile-ID bank selection (even=$0000, odd=$1000)
and vertical reflection. No original Vice: Project Doom assets.
This generator alone is NOT a native FCEUX framebuffer proof.
"""
import argparse
import hashlib
from pathlib import Path

from make_stage110_synthetic_midframe_rom import program
from make_stage124_native_quadrant_rom import initialization
from make_stage129_oam_sprite_rom import (
    sprite_initialization, explicit_sprite_palette_slot2,
    RENDER_SETUP, MASK_SETUP,
)

MODES = ("odd_normal", "odd_vertical", "even_normal", "even_vertical")
OAM_TILE_WRITE = bytes((0xA9, 2, 0x8D, 4, 0x20))
# PPUCTRL bit 5 selects 8x16 sprite height. BG table remains $1000.
SPRITE16_SETUP = bytes((0xA9, 0x38, 0x8D, 0, 0x20))


def _write_solid_tile(chr_data, offset, pattern):
    if pattern not in (1, 2, 3):
        raise ValueError("Nonzero two-bit sprite pattern required")
    if offset < 0 or offset + 16 > len(chr_data):
        raise ValueError("CHR tile bank overflow")
    chr_data[offset:offset+8] = bytes((0xFF if pattern & 1 else 0,)) * 8
    chr_data[offset+8:offset+16] = bytes((0xFF if pattern & 2 else 0,)) * 8


def make_rom(destination, mode):
    if mode not in MODES:
        raise ValueError("Four explicit 8x16 sprite modes required")
    odd = mode.startswith("odd_")
    vertical = mode.endswith("_vertical")
    base = program()
    if base.count(RENDER_SETUP) != 1 or base.count(MASK_SETUP) != 1:
        raise ValueError("Pinned raster fixture setup not unique")
    sprite = sprite_initialization(vflip=vertical)
    if sprite.count(OAM_TILE_WRITE) != 1:
        raise ValueError("Unexpected sprite tile OAM initialization")
    if odd:
        sprite = sprite.replace(OAM_TILE_WRITE,
                                bytes((0xA9, 3, 0x8D, 4, 0x20)), 1)
    payload = base.replace(
        RENDER_SETUP,
        initialization() + sprite + explicit_sprite_palette_slot2()
        + SPRITE16_SETUP, 1)
    payload = payload.replace(
        MASK_SETUP, bytes((0xA9, 0x1E, 0x8D, 1, 0x20)), 1)
    if len(payload) > 8192:
        raise ValueError("Generated 8x16 CPU program exceeds PRG bank")
    bank = bytearray(b"\xEA" * 8192)
    bank[:len(payload)] = payload
    prg = bytearray(bank * 4)
    prg[-6:] = b"\x00\xC0" * 3
    chr_data = bytearray(16384)
    # Existing background tile1 in the $1000 table: opaque pattern3.
    _write_solid_tile(chr_data, 1024 + 16, 3)
    # PPU table $0000, tile2/3: top pattern2, lower pattern1.
    _write_solid_tile(chr_data, 32, 2)
    _write_solid_tile(chr_data, 48, 1)
    # PPU table $1000, tile2/3: top pattern1, lower pattern3.
    _write_solid_tile(chr_data, 1024 + 32, 1)
    _write_solid_tile(chr_data, 1024 + 48, 3)
    result = b"NES\x1a" + bytes((2, 2, 0x40, 0)) + bytes(8) + prg + chr_data
    if len(result) != 49168:
        raise AssertionError("Mapper4 ROM layout changed")
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(result)
    return hashlib.sha256(result).hexdigest()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("destination", type=Path)
    cli.add_argument("--mode", choices=MODES, required=True)
    args = cli.parse_args()
    print("STAGE134_SYNTHETIC_8X16_OAM_ROM sha256=" +
          make_rom(args.destination, args.mode))
