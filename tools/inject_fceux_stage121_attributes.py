#!/usr/bin/env python3
"""Guarded Stage121 newppu attribute fetch-to-buffer-to-pixel observer.

Stage119 must already have instrumented the exact pinned PPU source.
Never modifies any original ROM, writes palette bytes or publishes screens.
"""
import argparse
from pathlib import Path

GUARD = b"VPD_NATIVE_SYNTHETIC_BG_ATTRIBUTES"
RECORD = b"\t\tunsigned vpd_stage119_ntaddr = 0;"
FETCH = b"\t\t\tat = CALL_PPUREAD(RefreshAddr);"
DECODE = b"\t\t\tat <<= 2;"
DRAW = (
    b"bgdata.main[bgtile].pt[1], pixel & 3, *ptr);"
)
HOOK = b"vpd_ppu_probe::stage121_pixel("


def patch(source):
    if not isinstance(source, bytes):
        raise TypeError("Expected raw bytes from pinned FCEUX source")
    if GUARD in source or HOOK in source:
        raise ValueError("Duplicate Stage121 instrumentation")
    anchors = (RECORD, FETCH, DECODE, DRAW)
    if any(source.count(a) != 1 for a in anchors):
        raise ValueError("Missing or ambiguous Stage119 buffered attribute sites")
    if (source.count(b"vpd_ppu_probe::stage119_pixel(") != 1 or
            source.count(b"vpd_stage119_ntaddr = NTRefreshAddr") != 1):
        raise ValueError("Stage119 fetch/pixel provenance was not installed")
    if b"\r\n" in source and source.count(b"\r\n") != source.count(b"\n"):
        raise ValueError("Mixed line endings")
    nl = b"\r\n" if b"\r\n" in source else b"\n"
    source = source.replace(
        RECORD, RECORD + nl + b"#ifdef " + GUARD + nl +
        b"\t\tunsigned vpd_stage121_ataddr = 0;" + nl +
        b"\t\tunsigned vpd_stage121_atraw = 0;" + nl +
        b"\t\tunsigned vpd_stage121_shift = 0;" + nl + b"#endif", 1)
    source = source.replace(
        FETCH, b"#ifdef " + GUARD + nl +
        b"\t\t\tvpd_stage121_ataddr = RefreshAddr;" + nl + b"#endif" +
        nl + FETCH + nl + b"#ifdef " + GUARD + nl +
        b"\t\t\tvpd_stage121_atraw = at;" + nl +
        b"\t\t\tvpd_stage121_shift = ((ppur.vt & 2) ? 4 : 0) +" +
        b" ((ppur.ht & 2) ? 2 : 0);" + nl + b"#endif", 1)
    source = source.replace(
        DRAW, DRAW + nl + b"#ifdef " + GUARD + nl +
        b"\t\t\t\t\t\t\t" + HOOK +
        b"sl, xt, xp, bgdata.main[bgtile].vpd_stage119_ntaddr, " +
        b"bgdata.main[bgtile].vpd_stage121_ataddr, " +
        b"bgdata.main[bgtile].vpd_stage121_atraw, " +
        b"bgdata.main[bgtile].vpd_stage121_shift, " +
        b"bgdata.main[bgtile].at, pixel & 3, " +
        b"(pixel & 3) | bgdata.main[bgtile].at);" + nl + b"#endif", 1)
    if (source.count(HOOK) != 1 or
            source.count(b"vpd_stage121_ataddr = RefreshAddr") != 1 or
            source.count(b"vpd_stage121_atraw = at") != 1):
        raise ValueError("Incomplete Stage121 native attribute provenance")
    return source


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_stage119_cpp", type=Path)
    parser.add_argument("private_stage121_cpp", type=Path)
    args = parser.parse_args()
    if args.private_stage119_cpp.resolve() == args.private_stage121_cpp.resolve():
        parser.error("Refuse source overwrite")
    result = patch(args.private_stage119_cpp.read_bytes())
    args.private_stage121_cpp.parent.mkdir(parents=True, exist_ok=True)
    args.private_stage121_cpp.write_bytes(result)
    print("Stage121 actual attribute address, raw byte, shift, palette bits and pixel hooks installed")
