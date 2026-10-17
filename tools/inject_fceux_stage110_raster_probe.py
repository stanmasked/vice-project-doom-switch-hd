#!/usr/bin/env python3
"""Insert stage110 raster-row+XBuf source hook into private pinned FCEUX copy."""
import argparse
from pathlib import Path

ANCHOR = b"vpd_ppu_probe::observe_native_bg_pixel(pixel & 3, *ptr);"
CALL = b"vpd_ppu_probe::stage110_raster_pixel(sl, pixel & 3, *ptr)"
GUARD = b"#ifdef VPD_NATIVE_SYNTHETIC_MIDFRAME_CHR"


def patch_raster(raw):
    if not isinstance(raw, bytes):
        raise TypeError("FCEUX source must be raw bytes")
    if raw.count(ANCHOR) != 1 or raw.count(b"vpd_ppu_probe::observe_native_bg_fetch") != 2:
        raise ValueError("Missing pinned stage107/108 pixel and fetch hooks")
    if CALL in raw or GUARD in raw:
        raise ValueError("Already instrumented")
    if b"\r\n" in raw and raw.count(b"\n") != raw.count(b"\r\n"):
        raise ValueError("Mixed source line endings")
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    new = ANCHOR + nl + GUARD + nl + b"\t\t\t\t\t\t\tvpd_ppu_probe::stage110_raster_pixel(sl, pixel & 3, *ptr);" + nl + b"#endif"
    result = raw.replace(ANCHOR, new, 1)
    if result.count(CALL) != 1 or result.count(GUARD) != 1:
        raise ValueError("Incomplete stage110 render hook")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage108_private_cpp", type=Path)
    parser.add_argument("stage110_private_cpp", type=Path)
    args = parser.parse_args()
    if args.stage108_private_cpp.resolve() == args.stage110_private_cpp.resolve():
        parser.error("Refuse in-place modification")
    result = patch_raster(args.stage108_private_cpp.read_bytes())
    args.stage110_private_cpp.parent.mkdir(parents=True, exist_ok=True)
    args.stage110_private_cpp.write_bytes(result)
    print("Stage110 controlled source raster hook installed in temporary FCEUX")
