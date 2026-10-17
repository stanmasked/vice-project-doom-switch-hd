#!/usr/bin/env python3
"""Guarded tile-source observation at pinned FCEUX final framebuffer assignment."""
import argparse
from pathlib import Path

ANCHOR = b"vpd_ppu_probe::stage110_raster_pixel(sl, pixel & 3, *ptr);"
CALL = b"vpd_ppu_probe::stage111_tile_pixel"
GUARD = b"#ifdef VPD_NATIVE_SYNTHETIC_BG_TILES"


def patch_tile_probe(source):
    if not isinstance(source, bytes):
        raise TypeError("Source must be bytes")
    if source.count(ANCHOR) != 1 or source.count(
            b"vpd_ppu_probe::observe_native_bg_fetch") != 2:
        raise ValueError("Missing verified previous BG hook sites")
    if CALL in source or GUARD in source:
        raise ValueError("Already patched")
    if b"\r\n" in source and source.count(b"\n") != source.count(b"\r\n"):
        raise ValueError("Mixed source line endings")
    nl = b"\r\n" if b"\r\n" in source else b"\n"
    new = (ANCHOR + nl + GUARD + nl +
           b"\t\t\t\t\t\t\tvpd_ppu_probe::stage111_tile_pixel(" +
           b"sl, xt, xp, bgtile, bgdata.main[bgtile].pt[0], " +
           b"bgdata.main[bgtile].pt[1], pixel & 3);" + nl + b"#endif")
    result = source.replace(ANCHOR, new, 1)
    if result.count(CALL) != 1 or result.count(GUARD) != 1:
        raise ValueError("Incomplete tile hook")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("private_output", type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.private_output.resolve():
        parser.error("Refusing to overwrite source")
    content = patch_tile_probe(args.source.read_bytes())
    args.private_output.parent.mkdir(parents=True, exist_ok=True)
    args.private_output.write_bytes(content)
    print("Stage111 private newppu tile hook patched")
