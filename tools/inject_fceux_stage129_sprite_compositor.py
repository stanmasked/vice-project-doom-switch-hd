#!/usr/bin/env python3
"""Stage129 guarded real FCEUX sprite-0 OAM and final framebuffer witness.

The hook lives inside the pinned newppu raster loop, not a separate
compositing reimplementation. Requires prior Stage121 buffered BG hooks.
"""
import argparse
from pathlib import Path

GUARD = b"VPD_NATIVE_SYNTHETIC_SPRITE_COLLISION"
START = b"bool havepixel = false;"
PATTERN = b"spixel |= (oam[5] & 1) << 1;"
DRAW = b"*ptr = PaletteAdjustPixel(pixelcolor);"
HOOK = b"vpd_ppu_probe::stage129_pixel("


def patch(source):
    if not isinstance(source, bytes):
        raise TypeError("Pinned upstream source must be bytes")
    if GUARD in source or HOOK in source:
        raise ValueError("Stage129 already instrumented")
    for anchor in (START, PATTERN, DRAW):
        if source.count(anchor) != 1:
            raise ValueError("Missing or duplicated real FCEUX sprite compositor anchor")
    if source.count(b"vpd_ppu_probe::stage124_pixel(") != 1:
        raise ValueError("Missing earlier live framebuffer provenance")
    if source.count(b"vpd_stage119_ntaddr = NTRefreshAddr") != 1:
        raise ValueError("Missing real background source address")
    if b"\r\n" in source and source.count(b"\r\n") != source.count(b"\n"):
        raise ValueError("Mixed FCEUX source line endings")
    nl = b"\r\n" if b"\r\n" in source else b"\n"
    start = (START + nl + b"#ifdef " + GUARD + nl +
             b"\t\t\t\t\t\tbool vpd_stage129_read=false;" + nl +
             b"\t\t\t\t\t\tunsigned vpd_stage129_pattern=0;" + nl +
             b"#endif")
    pattern = (PATTERN + nl + b"#ifdef " + GUARD + nl +
               b"\t\t\t\t\t\t\t\tif(s==0){vpd_stage129_read=true;"
               b"vpd_stage129_pattern=spixel;}" + nl + b"#endif")
    draw = (DRAW + nl + b"#ifdef " + GUARD + nl +
            b"\t\t\t\t\t\tif(oamcount>0) " + HOOK +
            b"sl, rasterpos, oamcount, oams[renderslot][0][0], " +
            b"oams[renderslot][0][1], oams[renderslot][0][2], " +
            b"oams[renderslot][0][3], vpd_stage129_read, " +
            b"vpd_stage129_pattern, havepixel, pixel & 3, " +
            b"pixelcolor, PPU_status, *ptr, " +
            b"bgdata.main[bgtile].vpd_stage119_ntaddr);" + nl +
            b"#endif")
    source = source.replace(START, start, 1)
    source = source.replace(PATTERN, pattern, 1)
    source = source.replace(DRAW, draw, 1)
    if source.count(HOOK) != 1:
        raise ValueError("Stage129 emitted no sprite framebuffer hook")
    return source


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("stage124_cpp", type=Path)
    cli.add_argument("stage129_cpp", type=Path)
    args = cli.parse_args()
    if args.stage124_cpp.resolve() == args.stage129_cpp.resolve():
        cli.error("In-place modification prohibited")
    result = patch(args.stage124_cpp.read_bytes())
    args.stage129_cpp.parent.mkdir(parents=True, exist_ok=True)
    args.stage129_cpp.write_bytes(result)
    print("Stage129 native FCEUX sprite pattern, OAM, hit and XBuf hook installed")
