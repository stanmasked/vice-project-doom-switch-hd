#!/usr/bin/env python3
"""Add source-guarded low/high CHR plane and record provenance to private newppu.

Requires the full pinned, previously instrumented Stage113 translation unit.
"""
import argparse
import re
from pathlib import Path

FETCH = re.compile(
    rb"(?m)^(\t+)pt\[(0|1)\] = CALL_PPUREAD\(RefreshAddr\);(?=\r?\n)"
)
BEGIN = b"vpd_ppu_probe::stage113_begin(sl, xt + 2);"
END = (
    b"vpd_ppu_probe::stage113_end(sl, xt + 2, "
    b"bgdata.main[xt + 2].pt[0], bgdata.main[xt + 2].pt[1]);"
)
DRAW = (
    b"vpd_ppu_probe::stage113_draw(sl, xt, xp, bgtile, "
    b"bgdata.main[bgtile].pt[0], bgdata.main[bgtile].pt[1]);"
)
GUARD = b"VPD_NATIVE_SYNTHETIC_BG_PLANE_PAIRS"


def inject_plane_pairs(raw):
    if not isinstance(raw, bytes):
        raise TypeError("FCEUX source must be raw bytes")
    if GUARD in raw or b"vpd_ppu_probe::stage114_" in raw:
        raise ValueError("Already installed")
    if (raw.count(BEGIN) != 1 or raw.count(END) != 1 or
            raw.count(DRAW) != 1 or
            raw.count(b"vpd_ppu_probe::observe_native_bg_fetch") != 2):
        raise ValueError("Unpinned/ambiguous Stage113 BGData provenance sites")
    if b"\r\n" in raw and raw.count(b"\r\n") != raw.count(b"\n"):
        raise ValueError("Mixed line endings")
    matches = list(FETCH.finditer(raw))
    if len(matches) != 2 or [m.group(2) for m in matches] != [b"0", b"1"]:
        raise ValueError("Incorrect low/high PPU-read order")
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    for m in reversed(matches):
        number = m.group(2)
        call = (b"vpd_ppu_probe::stage114_plane(" + number +
                b", RefreshAddr, pt[" + number + b"]);" )
        replace = (m.group(0) + nl + b"#ifdef " + GUARD + nl +
                   m.group(1) + b"if (ScreenON)" + nl +
                   m.group(1) + b"\t" + call + nl +
                   b"#endif")
        raw = raw[:m.start()] + replace + raw[m.end():]
    for anchor, name, args in (
        (BEGIN, b"stage114_begin", b"sl, xt + 2"),
        (END, b"stage114_end",
         b"sl, xt + 2, bgdata.main[xt + 2].pt[0], bgdata.main[xt + 2].pt[1]"),
        (DRAW, b"stage114_draw",
         b"sl, xt, xp, bgtile, bgdata.main[bgtile].pt[0], bgdata.main[bgtile].pt[1]"),
    ):
        tabs = b"\t\t\t\t" if name != b"stage114_draw" else b"\t\t\t\t\t\t\t"
        fragment = (anchor + nl + b"#ifdef " + GUARD + nl +
                    tabs + b"vpd_ppu_probe::" + name +
                    b"(" + args + b");" + nl + b"#endif")
        raw = raw.replace(anchor, fragment, 1)
    if (raw.count(b"vpd_ppu_probe::stage114_plane") != 2 or
            any(raw.count(b"vpd_ppu_probe::" + name) != 1 for name in
                (b"stage114_begin", b"stage114_end", b"stage114_draw"))):
        raise ValueError("Incomplete ordered PPU plane/read/draw hooks")
    return raw


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_stage113_ppu", type=Path)
    p.add_argument("private_stage114_ppu", type=Path)
    args = p.parse_args()
    if args.private_stage113_ppu.resolve() == args.private_stage114_ppu.resolve():
        p.error("Refuse in-place patch")
    result = inject_plane_pairs(args.private_stage113_ppu.read_bytes())
    args.private_stage114_ppu.parent.mkdir(parents=True, exist_ok=True)
    args.private_stage114_ppu.write_bytes(result)
    print("Stage114 low/high CHR plane pair hooks injected into private FCEUX")
