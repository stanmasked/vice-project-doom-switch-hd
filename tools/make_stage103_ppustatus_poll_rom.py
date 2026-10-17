#!/usr/bin/env python3
"""Stage103: synthesize an original iNES NROM polling $2002.

No commercial ROM bytes, screenshots or PPU contents are used.
"""
import argparse
import hashlib
from pathlib import Path

from make_stage100_synthetic_nrom import make_rom


def make_ppustatus_poll_rom(path):
    path = Path(path)
    make_rom(path)
    data = bytearray(path.read_bytes())
    # CPU C000: LDA $2002 ; JMP $C000. No values are stored or exported.
    data[16:22] = bytes((0xAD, 0x02, 0x20, 0x4C, 0x00, 0xC0))
    assert len(data) == 24592
    assert data[-8192:] == bytes(8192)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_output", type=Path)
    args = parser.parse_args()
    print("Stage103 synthetic NROM poll program created; sha256=" +
          make_ppustatus_poll_rom(args.private_output))


if __name__ == "__main__":
    main()
