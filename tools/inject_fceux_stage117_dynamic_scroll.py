#!/usr/bin/env python3
"""Pinned-source, synthetic-only native hooks for a mid-render $2005 write.

Observe ppur.fh after the real B2005 assignment and the actual two-plane
background byte selection at the final XBuf sink, without moving PPU events.
"""
import argparse
from pathlib import Path

REGISTER = b"\t\tppur.fh = V & 7;"
PIXEL = (
    b"vpd_ppu_probe::stage116_pixel(sl, xt, xp, bgtile, bgpx, ppur.fh, "
    b"bgdata.main[bgtile].pt[0], bgdata.main[bgtile].pt[1], pixel & 3);"
)
GUARD = b"VPD_NATIVE_SYNTHETIC_DYNAMIC_SCROLL"


def inject_dynamic_scroll(raw):
    if not isinstance(raw, bytes):
        raise TypeError("Source must be raw pinned FCEUX bytes")
    if GUARD in raw or b"vpd_ppu_probe::stage117_" in raw:
        raise ValueError("Stage117 source already instrumented")
    if (raw.count(REGISTER) != 1 or raw.count(PIXEL) != 1 or
            raw.count(b"vpd_ppu_probe::stage115_edge_draw") != 1 or
            raw.count(b"vpd_ppu_probe::stage110_raster_pixel") != 1):
        raise ValueError("Missing exact upstream PPU register or prior renderer hooks")
    if b"\r\n" in raw and raw.count(b"\r\n") != raw.count(b"\n"):
        raise ValueError("Mixed line endings in FCEUX source")
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    register = (REGISTER + nl + b"#ifdef " + GUARD + nl +
                b"\t\tvpd_ppu_probe::stage117_scroll_write("
                b"ppur.fh, ppur._ht);" + nl + b"#endif")
    pixel = (
        PIXEL + nl + b"#ifdef " + GUARD + nl +
        b"\t\t\t\t\t\t\tvpd_ppu_probe::stage117_pixel("
        b"sl, xt, xp, bgtile, bgpx, ppur.fh, "
        b"bgdata.main[bgtile].pt[0], bgdata.main[bgtile].pt[1], "
        b"pixel & 3);" + nl + b"#endif"
    )
    patched = raw.replace(REGISTER, register, 1).replace(PIXEL, pixel, 1)
    if patched.count(b"vpd_ppu_probe::stage117_scroll_write") != 1 or \
            patched.count(b"vpd_ppu_probe::stage117_pixel") != 1:
        raise ValueError("Incomplete native $2005 call site instrumentation")
    return patched


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_stage116_cpp", type=Path)
    parser.add_argument("private_stage117_cpp", type=Path)
    args = parser.parse_args()
    if args.private_stage116_cpp.resolve() == args.private_stage117_cpp.resolve():
        parser.error("Refusing in-place original PPU edit")
    patched = inject_dynamic_scroll(args.private_stage116_cpp.read_bytes())
    args.private_stage117_cpp.parent.mkdir(parents=True, exist_ok=True)
    args.private_stage117_cpp.write_bytes(patched)
    print("Stage117 dynamic fine-X scroll native PPU hooks installed")
