#!/usr/bin/env python3
"""Guarded final-framebuffer pixel observation for private patched FCEUX newppu."""
import argparse
import re
from pathlib import Path

ASSIGNMENT = re.compile(rb"(?m)^(\t+)\*ptr = PaletteAdjustPixel\(pixelcolor\);$")
CALL = b"vpd_ppu_probe::observe_native_bg_pixel"
GUARD = b"VPD_NATIVE_SYNTHETIC_BG_PIXELS"


def patch_pixel_sink(raw):
    if not isinstance(raw, bytes):
        raise TypeError("PPU source must be bytes")
    if CALL in raw or GUARD in raw:
        raise ValueError("Already instrumented")
    if (b'#include "vpd_newppu_raw_step_probe.h"' not in raw or
            b"VPD_NATIVE_SYNTHETIC_PRECLEAR" not in raw):
        raise ValueError("Stage98-105 private source patch missing")
    matches = list(ASSIGNMENT.finditer(raw))
    if len(matches) != 1:
        raise ValueError("Pinned final framebuffer assignment missing or ambiguous")
    if b"\r\n" in raw and raw.count(b"\n") != raw.count(b"\r\n"):
        raise ValueError("Mixed line endings")
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    match = matches[0]
    indentation = match.group(1)
    insertion = (
        match.group(0) + nl +
        b"#ifdef VPD_NATIVE_SYNTHETIC_BG_PIXELS" + nl +
        indentation + b"if (renderbgnow && renderbg && !havepixel)" + nl +
        indentation + b"\tvpd_ppu_probe::observe_native_bg_pixel(pixel & 3, *ptr);" + nl +
        b"#endif"
    )
    result = raw[:match.start()] + insertion + raw[match.end():]
    if result.count(CALL) != 1 or result.count(GUARD) != 1:
        raise ValueError("Incomplete native stage107 hook")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_stage105_ppu", type=Path)
    parser.add_argument("private_stage107_ppu", type=Path)
    opts = parser.parse_args()
    if opts.private_stage105_ppu.resolve() == opts.private_stage107_ppu.resolve():
        parser.error("Refuse to modify source in place")
    result = patch_pixel_sink(opts.private_stage105_ppu.read_bytes())
    opts.private_stage107_ppu.parent.mkdir(parents=True, exist_ok=True)
    opts.private_stage107_ppu.write_bytes(result)
    print("Stage107 final framebuffer hook patched into private FCEUX copy")
