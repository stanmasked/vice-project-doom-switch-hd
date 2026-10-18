#!/usr/bin/env python3
"""Stage151: source-anchored pre-render PPU reset and post-XBuf proof hooks.

Applies only after guarded Stage150/149 instrumentation. No commercial ROM.
"""
import argparse
from pathlib import Path

GUARD=b"VPD_NATIVE_SYNTHETIC_OAM_PRERENDER_BOUNDARY"
INCLUDE=b'#include "vpd_stage150_dynamic_oam_frame_probe.h"'
BEFORE=b"vpd_ppu_probe::stage141_before_reset(PPU_status);"
AFTER=b"vpd_ppu_probe::stage141_after_reset(PPU_status);"
PIXEL=(b"vpd_ppu_probe::stage150_pixel("
       b"sl,rasterpos,oamcounts[renderslot],PPU_status,*ptr,"
       b"Sprite16,pixelcolor,havepixel,pixel & 3);")


def patch(source):
    if not isinstance(source,bytes):
        raise TypeError("Expected pinned FCEUX C++ source bytes")
    if GUARD in source or b"vpd_ppu_probe::stage151_before_reset(" in source:
        raise ValueError("Stage151 already installed")
    if b"\r\n" in source and source.count(b"\r\n")!=source.count(b"\n"):
        raise ValueError("Pinned FCEUX uses mixed line endings")
    nl=b"\r\n" if b"\r\n" in source else b"\n"
    for marker in (INCLUDE,BEFORE,AFTER,PIXEL,b"PPU_status = 0;"):
        if source.count(marker)!=1:
            raise ValueError("Stage151 missing/ambiguous native source anchor "+
                             repr(marker))
    src=source.replace(b"\r\n",b"\n")
    before_pos=src.index(BEFORE)
    reset_pos=src.index(b"PPU_status = 0;")
    after_pos=src.index(AFTER)
    if not before_pos<reset_pos<after_pos:
        raise ValueError("Stage141 reset events are not around pinned PPU clear")
    # Same hook-site shape as the already validated Stage141 hooks.
    # Inserting separate compile guards keeps existing hooks untouched.
    include=INCLUDE+nl+b"#ifdef "+GUARD+nl+(
        b'#include "vpd_stage151_prerender_boundary.h"')+nl+b"#endif"
    before=BEFORE+nl+b"#ifdef "+GUARD+nl+(
        b"\t\tvpd_ppu_probe::stage151_before_reset(PPU_status);"
        )+nl+b"#endif"
    after=AFTER+nl+b"#ifdef "+GUARD+nl+(
        b"\t\tvpd_ppu_probe::stage151_after_reset(PPU_status);"
        )+nl+b"#endif"
    pixel=PIXEL+nl+b"#ifdef "+GUARD+nl+(
        b"\t\t\t\t\t\tvpd_ppu_probe::stage151_after_pixel();"
        )+nl+b"#endif"
    output=source.replace(INCLUDE,include,1)
    output=output.replace(BEFORE,before,1)
    output=output.replace(AFTER,after,1)
    output=output.replace(PIXEL,pixel,1)
    if (output.count(GUARD)!=4 or
        output.count(b"vpd_ppu_probe::stage151_before_reset(")!=1 or
        output.count(b"vpd_ppu_probe::stage151_after_reset(")!=1 or
        output.count(b"vpd_ppu_probe::stage151_after_pixel(")!=1):
        raise ValueError("Incomplete Stage151 guarded pre-render boundary")
    return output


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source_cpp",type=Path)
    cli.add_argument("patched_cpp",type=Path)
    args=cli.parse_args()
    if args.source_cpp.resolve()==args.patched_cpp.resolve():
        cli.error("Refusing in-place source mutation")
    result=patch(args.source_cpp.read_bytes())
    args.patched_cpp.parent.mkdir(parents=True,exist_ok=True)
    args.patched_cpp.write_bytes(result)
    print("Stage151 native pre-render reset and XBuf boundary hooks installed")
