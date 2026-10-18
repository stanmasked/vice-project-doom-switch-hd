#!/usr/bin/env python3
"""Stage137 guarded newppu OAM evaluation and final XBuf observation."""
import argparse
from pathlib import Path
GUARD=b"VPD_NATIVE_SYNTHETIC_NINE_OAM"
EVAL=b"oamcounts[scanslot] = oamcount;"
DRAW=b"*ptr = PaletteAdjustPixel(pixelcolor);"

def patch(data):
    if not isinstance(data,bytes):
        raise TypeError("Pinned C++ bytes required")
    if GUARD in data or b"vpd_ppu_probe::stage137_eval(" in data:
        raise ValueError("Duplicate Stage137 OAM hook")
    for anchor in (EVAL,DRAW,b"vpd_ppu_probe::stage135_pixel(",
                   b"vpd_ppu_probe::stage133_pixel("):
        if data.count(anchor)!=1:
            raise ValueError("Ambiguous/missing newppu OAM source anchor")
    if b"\r\n" in data and data.count(b"\r\n")!=data.count(b"\n"):
        raise ValueError("Mixed pinned FCEUX line endings")
    nl=b"\r\n" if b"\r\n" in data else b"\n"
    ev=(EVAL+nl+b"#ifdef "+GUARD+nl+
        b"\t\t\tif(oamcount>=8) vpd_ppu_probe::stage137_eval("
        b"yp,scanslot,oamcount,PPU_status,SPRAM[32],SPRAM[35],"
        +b",".join(b"oams[scanslot][%d][6]"%i for i in range(8))+
        b");"+nl+b"#endif")
    dr=(DRAW+nl+b"#ifdef "+GUARD+nl+
        b"\t\t\t\t\t\tvpd_ppu_probe::stage137_pixel("
        b"sl,rasterpos,renderslot,oamcounts[renderslot],"
        b"PPU_status,*ptr,Sprite16);"+nl+b"#endif")
    out=data.replace(EVAL,ev,1).replace(DRAW,dr,1)
    if out.count(GUARD)!=2 or out.count(
            b"vpd_ppu_probe::stage137_pixel(")!=1 or out.count(
            b"vpd_ppu_probe::stage137_eval(")!=1:
        raise ValueError("Incomplete native OAM overflow observation")
    return out

if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("previous_cpp",type=Path)
    cli.add_argument("patched_cpp",type=Path)
    args=cli.parse_args()
    if args.previous_cpp.resolve()==args.patched_cpp.resolve():
        cli.error("In-place patch refused")
    b=patch(args.previous_cpp.read_bytes())
    args.patched_cpp.parent.mkdir(parents=True,exist_ok=True)
    args.patched_cpp.write_bytes(b)
    print("Stage137 native eight-slot evaluation and ninth-spite XBuf instrumented")
