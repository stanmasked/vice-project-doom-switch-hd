#!/usr/bin/env python3
"""Original, generated mapper-4 CHR bank A/B control; never commit ROM output."""
import argparse
import hashlib
from pathlib import Path


def program(bank):
    if bank not in (0, 1):
        raise ValueError("CHR bank must be 0 or 1")
    code = bytearray()
    def lda(value):
        code.extend((0xA9, value))
    def sta(address):
        code.extend((0x8D, address & 0xff, address >> 8))

    lda(0); sta(0x2000); sta(0x2001)
    lda(0x3f); sta(0x2006)
    lda(0); sta(0x2006)
    for color in (0x0f, 0x16, 0x27, 0x30):
        lda(color); sta(0x2007)
    lda(0x10); sta(0x2000)  # background CHR address $1000
    lda(0x0a); sta(0x2001)  # background and left-eight enabled
    lda(2); sta(0x8000)     # MMC3 command 2 maps $1000
    lda(bank); sta(0x8001)
    loop = 0xc000 + len(code)
    code.extend((0xad, 0x02, 0x20, 0x4c, loop & 0xff, loop >> 8))
    return bytes(code)


def make_rom(path, bank):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    header = b"NES\x1a" + bytes((2, 2, 0x40, 0)) + bytes(8)
    prg8 = bytearray(b"\xea" * 8192)
    instructions = program(bank)
    prg8[:len(instructions)] = instructions
    prg = bytearray(prg8 * 4)
    prg[-6:] = b"\x00\xc0" * 3
    chr_data = bytearray(16384)
    chr_data[1024:2048] = b"\xff" * 1024
    output = header + prg + chr_data
    assert len(output) == 16 + 32768 + 16384
    destination.write_bytes(output)
    return hashlib.sha256(output).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--bank", type=int, choices=[0, 1], required=True)
    opts = parser.parse_args()
    print("Stage107 synthetic ROM generated privately: " + make_rom(opts.path, opts.bank))
