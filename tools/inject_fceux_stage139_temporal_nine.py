#!/usr/bin/env python3
"""Stage139 guarded native FCEUX OAM evaluation and XBuf scanline hooks."""
import argparse
from pathlib import Path

GUARD=b"VPD_NATIVE_SYNTHETIC_TEMPORAL_NINE"
EVAL=b"oamcounts[scanslot] = oamcount;"
DRAW=b"*ptr = PaletteAdjustPixel(pixelcolor);"


def patch(data):
    if not isinstance(data,bytes):
        raise TypeError("Pinned FCEUX source bytes required")
    if GUARD in data or b"vpd_ppu_probe::stage139_eval(" in data:
        raise ValueError("Stage139 duplicate injection")
    for anchor in (EVAL,DRAW,b"vpd_ppu_probe::stage137_eval(",
                   b"vpd_ppu_probe::stage137_pixel("):
        if data.count(anchor)!=1:
            raise ValueError("Missing/ambiguous source provenance anchor")
    if b"\r\n" in data and data.count(b"\r\n")!=data.count(b"\n"):
        raise ValueError("Mixed FCEUX source line endings")
    nl=b"\r\n" if b"\r\n" in data else b"\n"
    eval_hook=(EVAL+nl+b"#ifdef "+GUARD+nl+
        b"\t\t\tif(oamcount>=7 && (yp==124 || yp==132)) "
        b"vpd_ppu_probe::stage139_eval(yp,oamcount,PPU_status,"+
        b",".join(b"oams[scanslot][%d][6]"%i for i in range(8))+
        b");"+nl+b"#endif")
    pixel_hook=(DRAW+nl+b"#ifdef "+GUARD+nl+
        b"\t\t\t\t\t\tvpd_ppu_probe::stage139_pixel("
        b"sl,rasterpos,oamcounts[renderslot],PPU_status,*ptr,Sprite16);"+
        nl+b"#endif")
    result=data.replace(EVAL,eval_hook,1).replace(DRAW,pixel_hook,1)
    if result.count(GUARD)!=2 or result.count(
            b"vpd_ppu_probe::stage139_eval(")!=1 or result.count(
            b"vpd_ppu_probe::stage139_pixel(")!=1:
        raise ValueError("Stage139 real native source hook incomplete")
    return result


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("previous_cpp",type=Path)
    cli.add_argument("updated_cpp",type=Path)
    a=cli.parse_args()
    if a.previous_cpp.resolve()==a.updated_cpp.resolve():
        cli.error("In-place upstream mutation refused")
    a.updated_cpp.parent.mkdir(parents=True,exist_ok=True)
    a.updated_cpp.write_bytes(patch(a.previous_cpp.read_bytes()))
    print("Stage139 genuine newppu time-dependent OAM and XBuf hooks installed")
