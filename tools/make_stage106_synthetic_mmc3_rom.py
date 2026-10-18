#!/usr/bin/env python3
"""Construct an original synthetic mapper-4 MMC3 CHR-register-toggle test ROM."""
import argparse
import hashlib
from pathlib import Path

# C000:
# LDA $2002; LDA #$02; STA $8000; LDA $00; EOR #$01; STA $00;
# STA $8001; JMP $C000. Identical 8 KiB program in every PRG bank.
PROGRAM = bytes((
    0xAD, 0x02, 0x20, 0xA9, 0x02, 0x8D, 0x00, 0x80,
    0xA5, 0x00, 0x49, 0x01, 0x85, 0x00,
    0x8D, 0x01, 0x80, 0x4C, 0x00, 0xC0,
))


def make_mapper4_chr_toggle_rom(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = b"NES\x1a" + bytes((2, 2, 0x40, 0)) + bytes(8)
    bank = bytearray(b"\xea" * 8192)
    bank[:len(PROGRAM)] = PROGRAM
    prg = bytearray(bank * 4)
    prg[-6:] = bytes((0, 0xC0)) * 3
    # CHR content is intentionally all zero; *bank selection* is tested.
    payload = header + prg + bytes(16384)
    assert len(payload) == 16 + 32768 + 16384
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_destination", type=Path)
    args = parser.parse_args()
    print("Original synthetic MMC3 mapper-4 test built locally; SHA256=" +
          make_mapper4_chr_toggle_rom(args.private_destination))


if __name__ == "__main__":
    main()
