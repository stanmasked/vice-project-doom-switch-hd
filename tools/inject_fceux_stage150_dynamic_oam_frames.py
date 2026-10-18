#!/usr/bin/env python3
"""Stage150 private pinned FCEUX hooks for actual OAM-selection/XBuf frames.

Instruments source only after Stage149 CPU writes and existing Stage141
newppu hooks. No copied game data, no original ROM, no public captures.
"""
import argparse
from pathlib import Path

INCLUDE=b'#include "vpd_stage149_cpu_oam_probe.h"'
GUARD=b"VPD_NATIVE_SYNTHETIC_DYNAMIC_OAM_FRAMES"
EVAL=b"oamcounts[scanslot] = oamcount;"
DRAW=b"*ptr = PaletteAdjustPixel(pixelcolor);"


def patch(source):
    if not isinstance(source,bytes):
        raise TypeError("Stage150 requires byte-exact private FCEUX C++")
    if GUARD in source or b"vpd_ppu_probe::stage150_eval(" in source:
        raise ValueError("Stage150 instrumentation already present")
    if b"\r\n" in source and source.count(b"\r\n")!=source.count(b"\n"):
        raise ValueError("Mixed pinned FCEUX newline formatting")
    nl=b"\r\n" if b"\r\n" in source else b"\n"
    for marker in (INCLUDE,EVAL,DRAW,
                   b"vpd_ppu_probe::stage149_oam_data(",
                   b"vpd_ppu_probe::stage141_eval(",
                   b"vpd_ppu_probe::stage141_pixel("):
        if source.count(marker)!=1:
            raise ValueError("Missing or ambiguous native OAM/frame source anchor: "+
                             repr(marker))
    include=(INCLUDE+nl+b"#ifdef "+GUARD+nl+
             b'#include "vpd_stage150_dynamic_oam_frame_probe.h"'+nl+
             b"#endif")
    selected=(EVAL+nl+b"#ifdef "+GUARD+nl+
              b"\t\t\tif(oamcount==8 && yp==124) "+
              b"vpd_ppu_probe::stage150_eval("+
              b"yp,oamcount,PPU_status,SPRAM[31],SPRAM[32],SPRAM[35],"+
              b",".join(b"oams[scanslot][%d][6]"%i for i in range(8))+
              b");"+nl+b"#endif")
    xbuf=(DRAW+nl+b"#ifdef "+GUARD+nl+
          b"\t\t\t\t\t\tvpd_ppu_probe::stage150_pixel("+
          b"sl,rasterpos,oamcounts[renderslot],PPU_status,*ptr,"+
          b"Sprite16,pixelcolor,havepixel,pixel & 3);"+nl+b"#endif")
    output=source.replace(INCLUDE,include,1)
    output=output.replace(EVAL,selected,1)
    output=output.replace(DRAW,xbuf,1)
    if (output.count(GUARD)!=3 or
        output.count(b"vpd_ppu_probe::stage150_eval(")!=1 or
        output.count(b"vpd_ppu_probe::stage150_pixel(")!=1):
        raise ValueError("Incomplete native Stage150 sprite/frame source hooks")
    return output


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source_cpp",type=Path)
    cli.add_argument("patched_cpp",type=Path)
    args=cli.parse_args()
    if args.source_cpp.resolve()==args.patched_cpp.resolve():
        cli.error("Refusing to overwrite private source input")
    result=patch(args.source_cpp.read_bytes())
    args.patched_cpp.parent.mkdir(parents=True,exist_ok=True)
    args.patched_cpp.write_bytes(result)
    print("Stage150 actual native OAM selection and XBuf frame hooks installed")
