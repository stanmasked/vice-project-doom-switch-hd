#!/usr/bin/env python3
"""Source-guarded private FCEUX BGData::Record.Read begin/end and draw hooks.

Stage113 treats the buffered pattern record as evidence, not as a raw CHR
fetch happening at the moment of the later pixel assignment.
"""
import argparse
import re
from pathlib import Path

READ = re.compile(rb"(?m)^(\t+)bgdata\.main\[xt \+ 2\]\.Read\(\);(?=\r?\n)")
DRAW = b"bgdata.main[bgtile].pt[1], pixel & 3);"
GUARD = b"VPD_NATIVE_SYNTHETIC_BG_PREFETCH"
BEGIN = b"vpd_ppu_probe::stage113_begin"
END = b"vpd_ppu_probe::stage113_end"
CONSUME = b"vpd_ppu_probe::stage113_draw"


def patch_prefetch(source):
    if not isinstance(source, bytes):
        raise TypeError("Expected raw source bytes")
    if any(mark in source for mark in (BEGIN, END, CONSUME, GUARD)):
        raise ValueError("Already instrumented")
    if (source.count(b"vpd_ppu_probe::stage111_tile_pixel") != 1 or
            source.count(DRAW) != 1 or
            source.count(b"vpd_ppu_probe::observe_native_bg_fetch") != 2):
        raise ValueError("Missing native Stage111 source provenance")
    if b"\r\n" in source and source.count(b"\n") != source.count(b"\r\n"):
        raise ValueError("Mixed line endings")
    reads = list(READ.finditer(source))
    if len(reads) != 1:
        raise ValueError("Ambiguous source BGData.Record.Read site")
    nl = b"\r\n" if b"\r\n" in source else b"\n"
    match = reads[0]
    tab = match.group(1)
    replacement = (
        b"#ifdef " + GUARD + nl +
        tab + BEGIN + b"(sl, xt + 2);" + nl +
        b"#endif" + nl +
        match.group(0) + nl +
        b"#ifdef " + GUARD + nl +
        tab + END + b"(sl, xt + 2, bgdata.main[xt + 2].pt[0], " +
        b"bgdata.main[xt + 2].pt[1]);" + nl +
        b"#endif"
    )
    patched = source[:match.start()] + replacement + source[match.end():]
    draw = (DRAW + nl + b"#ifdef " + GUARD + nl +
            b"\t\t\t\t\t\t\t" + CONSUME +
            b"(sl, xt, xp, bgtile, bgdata.main[bgtile].pt[0], " +
            b"bgdata.main[bgtile].pt[1]);" + nl + b"#endif")
    patched = patched.replace(DRAW, draw, 1)
    if any(patched.count(call) != 1 for call in (BEGIN, END, CONSUME)):
        raise ValueError("Unbalanced Stage113 source observers")
    return patched


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_stage111_cpp", type=Path)
    parser.add_argument("private_stage113_cpp", type=Path)
    opts = parser.parse_args()
    if opts.private_stage111_cpp.resolve() == opts.private_stage113_cpp.resolve():
        parser.error("Refuse in-place patch")
    result = patch_prefetch(opts.private_stage111_cpp.read_bytes())
    opts.private_stage113_cpp.parent.mkdir(parents=True, exist_ok=True)
    opts.private_stage113_cpp.write_bytes(result)
    print("Stage113 begin/end record fetch and draw-site hooks installed")
