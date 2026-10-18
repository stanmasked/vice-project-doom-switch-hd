#!/usr/bin/env python3
"""Opt-in observation of the real newppu background CHR pattern reads.

Patch the *already* stage107-instrumented private pinned FCEUX source.
Only controlled, original synthetic mapper-4 ROMs may be used as evidence.
"""
import argparse
import re
from pathlib import Path

FETCH = re.compile(
    rb"(?m)^(\t+)pt\[(0|1)\] = CALL_PPUREAD\(RefreshAddr\);(?=\r?\n)"
)
CALL = b"vpd_ppu_probe::observe_native_bg_fetch"
GUARD = b"VPD_NATIVE_SYNTHETIC_BG_FETCH"


def patch_bg_fetch(raw):
    if not isinstance(raw, bytes):
        raise TypeError("FCEUX PPU source must be bytes")
    if CALL in raw or GUARD in raw:
        raise ValueError("Stage108 CHR pattern hook already inserted")
    if (raw.count(b"vpd_ppu_probe::observe_native_bg_pixel") != 1 or
            b'#include "vpd_newppu_raw_step_probe.h"' not in raw):
        raise ValueError("Missing private Stage107 patched FCEUX source")
    if b"\r\n" in raw and raw.count(b"\n") != raw.count(b"\r\n"):
        raise ValueError("Mixed pinned FCEUX line endings")
    matches = list(FETCH.finditer(raw))
    if len(matches) != 2 or [m.group(2) for m in matches] != [b"0", b"1"]:
        raise ValueError("Missing, duplicated or reordered background CHR fetch sites")
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    for match in reversed(matches):
        tab, plane = match.group(1), match.group(2)
        injection = (
            match.group(0) + nl +
            b"#ifdef VPD_NATIVE_SYNTHETIC_BG_FETCH" + nl +
            tab + b"if (ScreenON)" + nl +
            tab + b"\tvpd_ppu_probe::observe_native_bg_fetch(" +
            b"RefreshAddr, pt[" + plane + b"], " +
            (b"true" if plane == b"1" else b"false") + b");" + nl +
            b"#endif"
        )
        raw = raw[:match.start()] + injection + raw[match.end():]
    if raw.count(CALL) != 2 or raw.count(GUARD) != 2:
        raise ValueError("Incomplete BG fetch instrumentation")
    return raw


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage107_private_ppu", type=Path)
    parser.add_argument("stage108_private_output", type=Path)
    args = parser.parse_args()
    if args.stage107_private_ppu.resolve() == args.stage108_private_output.resolve():
        parser.error("Refuse in-place modification of a pinned source")
    output = patch_bg_fetch(args.stage107_private_ppu.read_bytes())
    args.stage108_private_output.parent.mkdir(parents=True, exist_ok=True)
    args.stage108_private_output.write_bytes(output)
    print("Stage108 newppu BG CHR read hooks generated in private FCEUX")
