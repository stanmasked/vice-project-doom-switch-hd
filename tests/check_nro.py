#!/usr/bin/env python3
"""Check the minimal NRO file structure; not a runtime/emulator test."""
from pathlib import Path
import struct
import sys

def check(path):
    data=Path(path).read_bytes()
    if len(data) < 0x50:
        raise ValueError("NRO is too small")
    if data[0x10:0x14] != b'NRO0':
        raise ValueError("Missing NRO0 signature at offset 0x10")
    declared=struct.unpack_from('<I', data, 0x18)[0]
    if declared < 0x50 or declared > len(data):
        raise ValueError(f"Unexpected NRO program size: {declared} vs {len(data)}")
    print(f"PASS: NRO magic and declared program size ({declared} bytes, file {len(data)} bytes)")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit("Usage: check_nro.py <built.nro>")
    check(sys.argv[1])
