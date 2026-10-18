#!/usr/bin/env python3
"""Pinned opt-in Stage124 native attribute-to-XBuf observer injection."""
import argparse
from pathlib import Path

GUARD = b"VPD_NATIVE_SYNTHETIC_QUADRANT_COLORS"
DRAW = b"bgdata.main[bgtile].pt[1], pixel & 3, *ptr);"
HOOK = b"vpd_ppu_probe::stage124_pixel("


def patch(source):
    if not isinstance(source, bytes):
        raise TypeError("Expected pinned FCEUX source bytes")
    if GUARD in source or HOOK in source:
        raise ValueError("Duplicate Stage124 patch")
    if (source.count(DRAW) != 1 or
            source.count(b"vpd_ppu_probe::stage121_pixel(") != 1 or
            source.count(b"vpd_stage121_ataddr = RefreshAddr") != 1 or
            source.count(b"vpd_stage119_ntaddr = NTRefreshAddr") != 1):
        raise ValueError("Missing buffered PPU provenance from Stage119 and Stage121")
    if b"\r\n" in source and source.count(b"\r\n") != source.count(b"\n"):
        raise ValueError("Mixed line endings")
    nl = b"\r\n" if b"\r\n" in source else b"\n"
    replacement = (
        DRAW + nl + b"#ifdef " + GUARD + nl +
        b"\t\t\t\t\t\t\t" + HOOK +
        b"sl, xt, xp, bgdata.main[bgtile].vpd_stage119_ntaddr, " +
        b"bgdata.main[bgtile].vpd_stage121_ataddr, " +
        b"bgdata.main[bgtile].vpd_stage121_atraw, " +
        b"bgdata.main[bgtile].vpd_stage121_shift, " +
        b"bgdata.main[bgtile].at, pixel & 3, pixel, " +
        b"pixelcolor, *ptr);" + nl + b"#endif"
    )
    result = source.replace(DRAW, replacement, 1)
    if result.count(HOOK) != 1:
        raise ValueError("Incomplete Stage124 pixel observer")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage121_cpp", type=Path)
    p.add_argument("stage124_cpp", type=Path)
    args = p.parse_args()
    if args.stage121_cpp.resolve() == args.stage124_cpp.resolve():
        p.error("Refuse in-place patch")
    result = patch(args.stage121_cpp.read_bytes())
    args.stage124_cpp.parent.mkdir(parents=True, exist_ok=True)
    args.stage124_cpp.write_bytes(result)
    print("Stage124 real buffered attribute, palette and XBuf observer installed")
