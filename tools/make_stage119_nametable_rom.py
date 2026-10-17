#!/usr/bin/env python3
"""Synthetic-only Mapper-4 patterned nametable and tile-ID graphics test.

Uses the original stage118 CPU program with two $2005 pairs, injecting a
separate PPU-disabled nametable initialization before rendering is enabled.
All ROMs are generated in temporary private CI directories.
"""
import argparse
import hashlib
from pathlib import Path
from make_stage110_synthetic_midframe_rom import program

START_RENDER_SETUP = bytes((0xa9, 0x10, 0x8d, 0x00, 0x20))


def nametable_init():
    # Write 1024 entries to $2000-$23FF. The first 960 are alternating
    # tile IDs 0,1,0,1... and the last 64 are attribute bytes.
    # 6502: LDX #0; TXA; AND #1; STA $2007; INX; BNE -9.
    loop = bytes((0xa2, 0, 0x8a, 0x29, 1, 0x8d, 7, 0x20,
                  0xe8, 0xd0, 0xf7))
    return (bytes((0xa9, 0x20, 0x8d, 6, 0x20,
                   0xa9, 0, 0x8d, 6, 0x20)) +
            loop * 4 +
            # Reset VRAM and both $2005 X/Y latches before drawing.
            bytes((0xa9, 0x20, 0x8d, 6, 0x20,
                   0xa9, 0, 0x8d, 6, 0x20,
                   0xa9, 0, 0x8d, 5, 0x20, 0x8d, 5, 0x20)))


def make_rom(dest, *, first=3, differentiated=True, switch=True):
    if type(first) is not int or first not in (1, 3, 5, 7):
        raise ValueError("First fine X must be 1,3,5,7")
    if type(differentiated) is not bool or type(switch) is not bool:
        raise ValueError("Control flags must be booleans")
    baseline = program(switch=switch, dynamic_fine_scroll=first,
                       second_dynamic_scroll=16-first)
    if baseline.count(START_RENDER_SETUP) != 1:
        raise ValueError("Original CPU program signature changed")
    payload = baseline.replace(START_RENDER_SETUP,
                               nametable_init() + START_RENDER_SETUP, 1)
    if len(payload) > 8192:
        raise ValueError("Generated CPU program exceeds 8 KiB PRG bank")
    prg = bytearray(b"\xea" * 8192)
    prg[:len(payload)] = payload
    four = bytearray(prg * 4)
    four[-6:] = b"\x00\xc0" * 3
    chr_data = bytearray(16384)
    if differentiated:
        # $8001=1 maps bank 1 to BG $1000; alternating tile IDs have
        # visibly different low/high planes inside that bank.
        for tile in range(1, 64, 2):
            start = 1024 + tile*16
            chr_data[start:start+16] = b"\xff"*16
    image = b"NES\x1a" + bytes((2, 2, 0x40, 0)) + bytes(8) + four + chr_data
    assert len(image) == 49168
    output = Path(dest)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(image)
    return hashlib.sha256(image).hexdigest()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("destination", type=Path)
    p.add_argument("--first", type=int, default=3)
    p.add_argument("--uniform-control", action="store_true")
    p.add_argument("--no-bank-change", action="store_true")
    args = p.parse_args()
    print("STAGE119_SYNTHETIC_NAMETABLE_ROM sha256=" +
          make_rom(args.destination, first=args.first,
                   differentiated=not args.uniform_control,
                   switch=not args.no_bank_change))
