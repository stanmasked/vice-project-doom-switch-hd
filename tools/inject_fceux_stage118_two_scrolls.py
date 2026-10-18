#!/usr/bin/env python3
"""Pin two synthetic PPU observers to existing FCEUX register and pixel hooks."""
import argparse
from pathlib import Path

WRITE = b"vpd_ppu_probe::stage117_scroll_write(ppur.fh, ppur._ht);"
PIXEL = (b"vpd_ppu_probe::stage117_pixel(sl, xt, xp, bgtile, bgpx, ppur.fh, "
         b"bgdata.main[bgtile].pt[0], bgdata.main[bgtile].pt[1], pixel & 3);")
MACRO = b"VPD_NATIVE_SYNTHETIC_TWO_SCROLLS"


def inject_two_scrolls(data):
    if not isinstance(data, bytes):
        raise TypeError("Expected raw source bytes")
    if MACRO in data or b"vpd_ppu_probe::stage118_" in data:
        raise ValueError("Already instrumented")
    if (data.count(WRITE) != 1 or data.count(PIXEL) != 1 or
            data.count(b"vpd_ppu_probe::stage116_pixel") != 1 or
            data.count(b"vpd_ppu_probe::stage110_raster_pixel") != 1):
        raise ValueError("Missing exact pinned register and XBuf hook sites")
    if b"\r\n" in data and data.count(b"\r\n") != data.count(b"\n"):
        raise ValueError("Mixed source line endings")
    nl = b"\r\n" if b"\r\n" in data else b"\n"
    new_write = (WRITE + nl + b"#ifdef " + MACRO + nl +
                 b"\t\tvpd_ppu_probe::stage118_write(ppur.fh, ppur._ht);" +
                 nl + b"#endif")
    new_pixel = (PIXEL + nl + b"#ifdef " + MACRO + nl +
                 b"\t\t\t\t\t\t\tvpd_ppu_probe::stage118_pixel("
                 b"sl, xt, xp, bgtile, bgpx, ppur.fh, "
                 b"bgdata.main[bgtile].pt[0], "
                 b"bgdata.main[bgtile].pt[1], pixel & 3);" + nl +
                 b"#endif")
    new = data.replace(WRITE, new_write, 1).replace(PIXEL, new_pixel, 1)
    if (new.count(b"vpd_ppu_probe::stage118_write") != 1 or
            new.count(b"vpd_ppu_probe::stage118_pixel") != 1):
        raise ValueError("Incomplete Stage118 native observer")
    return new


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_stage117_ppu", type=Path)
    p.add_argument("private_stage118_ppu", type=Path)
    opts = p.parse_args()
    if opts.private_stage117_ppu.resolve() == opts.private_stage118_ppu.resolve():
        p.error("Refuse in-place source modifications")
    contents = inject_two_scrolls(opts.private_stage117_ppu.read_bytes())
    opts.private_stage118_ppu.parent.mkdir(parents=True, exist_ok=True)
    opts.private_stage118_ppu.write_bytes(contents)
    print("Stage118 two $2005 write-to-XBuf observers installed")
