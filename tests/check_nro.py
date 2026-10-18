#!/usr/bin/env python3
"""Validate complete NRO section and ASET bounds; not a runtime test."""
from pathlib import Path
import struct
import sys


def check_bytes(data):
    if len(data) < 0x80 or data[0x10:0x14] != b'NRO0':
        raise ValueError("Missing or truncated NRO0 header")
    version, declared, flags = struct.unpack_from("<III", data, 0x14)
    if version != 0 or flags != 0:
        raise ValueError("Unexpected NRO header version/flags")
    if declared < 0x80 or declared > len(data) or declared % 0x1000:
        raise ValueError("NRO program size invalid or misaligned")
    sections = [struct.unpack_from("<II", data, offset)
                for offset in (0x20, 0x28, 0x30)]
    if sections[0][0] != 0:
        raise ValueError("Text segment must start at offset zero")
    for i, (offset, size) in enumerate(sections):
        if not size or offset % 0x1000 or size % 0x1000:
            raise ValueError("NRO segment size/alignment invalid")
        if offset + size > declared:
            raise ValueError("NRO segment exceeds declared program size")
        if i and offset != sections[i-1][0] + sections[i-1][1]:
            raise ValueError("NRO sections overlap or have gaps")
    if sections[-1][0] + sections[-1][1] != declared:
        raise ValueError("NRO sections do not cover program size")
    bss = struct.unpack_from("<I", data, 0x38)[0]
    if bss > 64*1024*1024 or bss % 0x1000:
        raise ValueError("NRO BSS size invalid")
    if not any(data[0x40:0x60]):
        raise ValueError("NRO build identity missing")
    asset_count = 0
    if len(data) > declared:
        suffix = data[declared:]
        if len(suffix) < 0x38 or suffix[:4] != b"ASET":
            raise ValueError("Invalid NRO homebrew asset header")
        if struct.unpack_from("<I", suffix, 4)[0] != 0:
            raise ValueError("Unsupported NRO asset header version")
        ranges = []
        for pos in (8, 24, 40):
            offset, size = struct.unpack_from("<QQ", suffix, pos)
            if (offset == 0) != (size == 0):
                raise ValueError("Incomplete NRO asset descriptor")
            if size:
                if offset < 0x38 or offset > len(suffix) or size > len(suffix)-offset:
                    raise ValueError("NRO asset exceeds file bounds")
                for start, end in ranges:
                    if not (offset + size <= start or offset >= end):
                        raise ValueError("NRO asset descriptors overlap")
                ranges.append((offset, offset+size))
                asset_count += 1
        if ranges and max(end for _, end in ranges) != len(suffix):
            raise ValueError("Unexpected data after final NRO asset")
        if not ranges and len(suffix) != 0x38:
            raise ValueError("Unaccounted NRO asset data")
    return declared, asset_count


def check(path):
    data = Path(path).read_bytes()
    declared, assets = check_bytes(data)
    print(f"PASS: NRO section layout, build ID and ASET bounds "
          f"({declared} program bytes, {len(data)} total, assets={assets}; "
          "runtime_proven=no)")
    return declared, assets


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: check_nro.py <built.nro>")
    check(sys.argv[1])
