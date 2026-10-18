#!/usr/bin/env python3
"""Guarded synthetic scanline-edge two-background-record instrumentation.

Pin both source sites: the final two BGData::Record.Read calls at line end,
and the already attached Stage114 final XBuf tile sink. The original loop
must remain a loop; wrapping with braces preserves its original execution.
"""
import argparse
import re
from pathlib import Path

TAIL = re.compile(
    rb"(?m)^(\t+)for \(int xt = 0; xt < 2; xt\+\+\)\r?\n"
    rb"(\t+)bgdata\.main\[xt\]\.Read\(\);(?=\r?\n)"
)
DRAW = (
    b"vpd_ppu_probe::stage114_draw(sl, xt, xp, bgtile, "
    b"bgdata.main[bgtile].pt[0], bgdata.main[bgtile].pt[1]);"
)
GUARD = b"VPD_NATIVE_SYNTHETIC_SCANLINE_CARRY"
READ_CALL = b"vpd_ppu_probe::stage115_edge_read"
DRAW_CALL = b"vpd_ppu_probe::stage115_edge_draw"


def inject_edge_carry(raw):
    if not isinstance(raw, bytes):
        raise TypeError("Expected raw FCEUX source bytes")
    if GUARD in raw or READ_CALL in raw or DRAW_CALL in raw:
        raise ValueError("Scanline carry observation already instrumented")
    if (raw.count(DRAW) != 1 or
            raw.count(b"vpd_ppu_probe::stage113_draw") != 1 or
            raw.count(b"vpd_ppu_probe::stage114_plane") != 2):
        raise ValueError("Pinned Stage114 source/provenance site missing")
    if b"\r\n" in raw and raw.count(b"\n") != raw.count(b"\r\n"):
        raise ValueError("Mixed source line endings")
    matches = list(TAIL.finditer(raw))
    if len(matches) != 1:
        raise ValueError("Ambiguous newppu scanline-edge two-tile loop")
    m = matches[0]
    if len(m.group(2)) != len(m.group(1)) + 1:
        raise ValueError("Unexpected FCEUX tile-fetch nesting")
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    start, inner = m.group(1), m.group(2)
    replacement = (
        start + b"for (int xt = 0; xt < 2; xt++) {" + nl +
        inner + b"bgdata.main[xt].Read();" + nl +
        b"#ifdef " + GUARD + nl +
        inner + READ_CALL + b"(sl, xt, bgdata.main[xt].pt[0], " +
        b"bgdata.main[xt].pt[1]);" + nl +
        b"#endif" + nl + start + b"}"
    )
    raw = raw[:m.start()] + replacement + raw[m.end():]
    render = (
        DRAW + nl + b"#ifdef " + GUARD + nl +
        b"\t\t\t\t\t\t\t" + DRAW_CALL +
        b"(sl, xt, xp, bgtile, ppur.fh, " +
        b"bgdata.main[bgtile].pt[0], bgdata.main[bgtile].pt[1]);" +
        nl + b"#endif"
    )
    raw = raw.replace(DRAW, render, 1)
    if raw.count(READ_CALL) != 1 or raw.count(DRAW_CALL) != 1:
        raise ValueError("Unbalanced native scanline carry source hooks")
    return raw


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_stage114_cpp", type=Path)
    p.add_argument("private_stage115_cpp", type=Path)
    args = p.parse_args()
    if args.private_stage114_cpp.resolve() == args.private_stage115_cpp.resolve():
        p.error("Refusing in-place FCEUX source patch")
    output = inject_edge_carry(args.private_stage114_cpp.read_bytes())
    args.private_stage115_cpp.parent.mkdir(parents=True, exist_ok=True)
    args.private_stage115_cpp.write_bytes(output)
    print("Stage115 private FCEUX line-edge carry provenance observer installed")
