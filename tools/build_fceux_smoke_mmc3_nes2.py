#!/usr/bin/env python3
"""Ephemeral entirely invented NES 2.0 / MMC3 test cartridge for FCEUX CI.

Mirrors only the STANDARD cartridge layout of an MMC3 128KiB PRG/128KiB CHR
NES2.0 game. No proprietary code, CHR patterns or ROM payload are included.
"""
import argparse
from pathlib import Path

from build_fceux_smoke_rom import build_rom as build_nrom

HEADER=b"NES\x1a"+bytes([8,16,0x40,0x08,0,0,0,0,0,0,0,1])
PRG_SIZE=131072
CHR_SIZE=131072


def build_rom():
    # Independently created $4016 controller polling loop, relocated into
    # MMC3's fixed final 8KiB PRG bank at $E000.
    original=build_nrom()[16:16+49]
    assert original[46:49]==b"\x4c\x1c\x80"
    # Invented MMC3 bank-switch writes inside the controller-polling loop.
    # R0 odd 0x7D maps the aligned 1KiB pair 124/125;
    # R2 bank 0x7E maps bank 126. No original game bytes involved.
    mapped=bytes([
        0xA9,0x00,0x8D,0x00,0x80,
        0xA9,0x7D,0x8D,0x01,0x80,
        0xA9,0x02,0x8D,0x00,0x80,
        0xA9,0x7E,0x8D,0x01,0x80
    ])
    program=original[:46]+mapped+b"\x4c\x1c\xe0"
    prg=bytearray([0xea]*PRG_SIZE)
    prg[-8192:-8192+len(program)]=program
    prg[-6:]=b"\x00\xe0"*3  # IRQ, RESET, NMI all point to $E000
    return HEADER+bytes(prg)+bytes(CHR_SIZE)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True,type=Path)
    a=parser.parse_args()
    if a.output.exists() or a.output.is_symlink():
        parser.error("refusing to overwrite an existing test ROM")
    if not a.output.parent.is_dir():
        parser.error("output parent must exist")
    with a.output.open("xb") as file:
        file.write(build_rom())
    print("SYNTHETIC_NES2_MMC3_CREATED original_game_proven=no")


if __name__=="__main__":
    main()
