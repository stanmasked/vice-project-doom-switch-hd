#!/usr/bin/env python3
"""Generate an original minimal iNES NROM in ephemeral private storage only."""
import argparse
import hashlib
from pathlib import Path


def make_rom(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = b"NES\x1a" + bytes((1, 1)) + bytes(10)
    prg = bytearray(b"\xEA" * 16384)
    # C000: LDA #08; STA $2001 (enable BG); JMP C005.
    prg[:8] = bytes((0xA9, 0x08, 0x8D, 0x01, 0x20, 0x4C, 0x05, 0xC0))
    prg[-6:] = bytes((0, 0xC0)) * 3
    data = header + prg + bytes(8192)
    assert len(data) == 16 + 16384 + 8192
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    print("Synthetic ROM created locally sha256=" + make_rom(args.path))


if __name__ == "__main__":
    main()
