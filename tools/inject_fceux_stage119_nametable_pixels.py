#!/usr/bin/env python3
"""Guarded native observer of consumed PPU nametable ID and final BG pixel."""
import argparse
from pathlib import Path

PIXEL = (
    b"vpd_ppu_probe::stage118_pixel(sl, xt, xp, bgtile, bgpx, ppur.fh, "
    b"bgdata.main[bgtile].pt[0], bgdata.main[bgtile].pt[1], pixel & 3);"
)
WRITE = b"vpd_ppu_probe::stage118_write(ppur.fh, ppur._ht);"
GUARD = b"VPD_NATIVE_SYNTHETIC_NAMETABLE_IDS"
RECORD = b"\t\tuint8 nt, pecnt, at, pt[2], qtnt;"
READ_NT = b"\t\t\tnt = CALL_PPUREAD(RefreshAddr);"


def patch(source):
    if not isinstance(source, bytes):
        raise TypeError("Expected raw FCEUX source")
    if GUARD in source or b"vpd_ppu_probe::stage119_" in source:
        raise ValueError("Already instrumented")
    if (source.count(PIXEL) != 1 or source.count(WRITE) != 1 or
            source.count(b"vpd_ppu_probe::stage115_edge_read") != 1 or
            source.count(RECORD) != 1 or source.count(READ_NT) != 1):
        raise ValueError("Pinned PPU source write/read/pixel provenance missing")
    if b"\r\n" in source and source.count(b"\r\n") != source.count(b"\n"):
        raise ValueError("Mixed line endings")
    nl = b"\r\n" if b"\r\n" in source else b"\n"
    record = (RECORD + nl + b"#ifdef " + GUARD + nl +
              b"\t\tunsigned vpd_stage119_ntaddr = 0;" + nl + b"#endif")
    read = (READ_NT + nl + b"#ifdef " + GUARD + nl +
            b"\t\t\tvpd_stage119_ntaddr = NTRefreshAddr;" +
            nl + b"#endif")
    write = WRITE + nl + b"#ifdef " + GUARD + nl + (
        b"\t\tvpd_ppu_probe::stage119_write(ppur.fh, ppur._ht);" +
        nl + b"#endif"
    )
    draw = PIXEL + nl + b"#ifdef " + GUARD + nl + (
        b"\t\t\t\t\t\t\tvpd_ppu_probe::stage119_pixel("
        b"sl, xt, xp, bgtile, bgpx, ppur.fh, ppur.ht, "
        b"bgdata.main[bgtile].nt, "
        b"bgdata.main[bgtile].vpd_stage119_ntaddr, "
        b"bgdata.main[bgtile].pt[0], "
        b"bgdata.main[bgtile].pt[1], pixel & 3, *ptr);" +
        nl + b"#endif"
    )
    patched = (source.replace(RECORD, record, 1).replace(READ_NT, read, 1)
               .replace(WRITE, write, 1).replace(PIXEL, draw, 1))
    if (patched.count(b"vpd_ppu_probe::stage119_write") != 1 or
            patched.count(b"vpd_ppu_probe::stage119_pixel") != 1 or
            patched.count(b"vpd_stage119_ntaddr = NTRefreshAddr") != 1):
        raise ValueError("Incomplete native nametable-to-XBuf instrumentation")
    return patched


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_stage118_ppu", type=Path)
    p.add_argument("private_stage119_ppu", type=Path)
    a = p.parse_args()
    if a.private_stage118_ppu.resolve() == a.private_stage119_ppu.resolve():
        p.error("Refuse in-place source patch")
    out = patch(a.private_stage118_ppu.read_bytes())
    a.private_stage119_ppu.parent.mkdir(parents=True, exist_ok=True)
    a.private_stage119_ppu.write_bytes(out)
    print("Stage119 actual rendered nametable ID, CHR and XBuf hooks installed")
