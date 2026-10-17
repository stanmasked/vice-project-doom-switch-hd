#!/usr/bin/env python3
"""Observe source fine-scroll and two line-carried BGData pattern records.

Only adds conditional probes to previously verified Stage115 instrumentation
in temporary source. No retail ROM or hardware raster claim.
"""
import argparse
from pathlib import Path

READ = (
    b"vpd_ppu_probe::stage115_edge_read(sl, xt, "
    b"bgdata.main[xt].pt[0], bgdata.main[xt].pt[1]);"
)
DRAW = (
    b"vpd_ppu_probe::stage115_edge_draw(sl, xt, xp, bgtile, ppur.fh, "
    b"bgdata.main[bgtile].pt[0], bgdata.main[bgtile].pt[1]);"
)
FLAG = b"VPD_NATIVE_SYNTHETIC_FINE_SCROLL"


def inject_fine_scroll(raw):
    if not isinstance(raw, bytes):
        raise TypeError("Expected original pinned source bytes")
    if FLAG in raw or b"vpd_ppu_probe::stage116_" in raw:
        raise ValueError("Already patched")
    if (raw.count(READ) != 1 or raw.count(DRAW) != 1 or
            raw.count(b"vpd_ppu_probe::stage114_plane") != 2):
        raise ValueError("Missing unique native Stage115 pixel+read sources")
    if b"\r\n" in raw and raw.count(b"\n") != raw.count(b"\r\n"):
        raise ValueError("Mixed line endings")
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    read = (READ + nl + b"#ifdef " + FLAG + nl +
            b"\t\t\t\tvpd_ppu_probe::stage116_edge_read("
            b"sl, xt, bgdata.main[xt].pt[0], bgdata.main[xt].pt[1]);" +
            nl + b"#endif")
    draw = (DRAW + nl + b"#ifdef " + FLAG + nl +
            b"\t\t\t\t\t\t\tvpd_ppu_probe::stage116_pixel("
            b"sl, xt, xp, bgtile, bgpx, ppur.fh, "
            b"bgdata.main[bgtile].pt[0], bgdata.main[bgtile].pt[1], "
            b"pixel & 3);" + nl + b"#endif")
    result = raw.replace(READ, read, 1).replace(DRAW, draw, 1)
    if (result.count(b"vpd_ppu_probe::stage116_edge_read") != 1 or
            result.count(b"vpd_ppu_probe::stage116_pixel") != 1):
        raise ValueError("Unable to audit native source hook coverage")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_stage115_ppu", type=Path)
    parser.add_argument("private_stage116_ppu", type=Path)
    args = parser.parse_args()
    if args.private_stage115_ppu.resolve() == args.private_stage116_ppu.resolve():
        parser.error("Refuse to overwrite pinned source")
    patched = inject_fine_scroll(args.private_stage115_ppu.read_bytes())
    args.private_stage116_ppu.parent.mkdir(parents=True, exist_ok=True)
    args.private_stage116_ppu.write_bytes(patched)
    print("Stage116 FCEUX private fine-scroll/tile carry hooks installed")
