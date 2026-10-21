#!/usr/bin/env python3
"""Invented 6502 test program. Only emit into an ephemeral CI path."""
import argparse
from pathlib import Path

HEADER=b"NES\x1a"+bytes([2,1,0,0])+bytes(8)
PRG_SIZE=32768
CHR_SIZE=8192

def build_rom():
    code=bytearray([
        0x78,0xD8,0xA2,0xFF,0x9A,
        0xA9,0x00,0x8D,0x00,0x20,0x8D,0x01,0x20,
        0xA9,0x3F,0x8D,0x06,0x20,
        0xA9,0x00,0x8D,0x06,0x20,
        0xA9,0x21,0x8D,0x07,0x20
    ])
    destination=0x8000+len(code)
    code.extend((0x4C,destination&255,destination>>8))
    prg=bytearray([0xEA]*PRG_SIZE)
    prg[:len(code)]=code
    prg[-6:]=b"\x00\x80"*3
    return HEADER+bytes(prg)+bytes(CHR_SIZE)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.output.is_symlink() or args.output.exists():
        p.error("refuse to overwrite an existing ROM")
    if not args.output.parent.is_dir():
        p.error("output folder missing")
    with args.output.open("xb") as stream:stream.write(build_rom())
    print("SYNTHETIC_NES_CREATED original_game_proven=no")

if __name__=="__main__":main()
