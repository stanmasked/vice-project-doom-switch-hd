#!/usr/bin/env python3
"""Guarded Stage131 dual-OAM raster source and final XBuf hook."""
import argparse
from pathlib import Path

GUARD=b"VPD_NATIVE_SYNTHETIC_DUAL_SPRITE"
START=b"bool havepixel = false;"
PATTERN=b"spixel |= (oam[5] & 1) << 1;"
CLAIM=b"havepixel = true;"
DRAW=b"*ptr = PaletteAdjustPixel(pixelcolor);"
HOOK=b"vpd_ppu_probe::stage131_pixel("


def patch(source):
    if not isinstance(source,bytes):
        raise TypeError("Pinned FCEUX source bytes required")
    if GUARD in source or HOOK in source:
        raise ValueError("Already instrumented for dual OAM")
    for text in (START,PATTERN,CLAIM,DRAW):
        if source.count(text)!=1:
            raise ValueError("Untrusted FCEUX dual sprite hook anchor")
    if (source.count(b"vpd_ppu_probe::stage129_pixel(")!=1 or
            source.count(b"vpd_stage119_ntaddr = NTRefreshAddr")!=1):
        raise ValueError("Missing earlier native OAM/nametable provenance")
    if b"\r\n" in source and source.count(b"\r\n") != source.count(b"\n"):
        raise ValueError("Mixed upstream source line endings")
    nl=b"\r\n" if b"\r\n" in source else b"\n"
    source=source.replace(START,START+nl+b"#ifdef "+GUARD+nl+
        b"\t\t\t\t\t\tbool vpd131_seen0=false,vpd131_seen1=false;"+nl+
        b"\t\t\t\t\t\tunsigned vpd131_pat0=0,vpd131_pat1=0;"+nl+
        b"\t\t\t\t\t\tint vpd131_claim=-1;"+nl+b"#endif",1)
    source=source.replace(PATTERN,PATTERN+nl+b"#ifdef "+GUARD+nl+
        b"\t\t\t\t\t\t\t\tif(s==0){vpd131_seen0=true;vpd131_pat0=spixel;}"+nl+
        b"\t\t\t\t\t\t\t\tif(s==1){vpd131_seen1=true;vpd131_pat1=spixel;}"+nl+
        b"#endif",1)
    source=source.replace(CLAIM,CLAIM+nl+b"#ifdef "+GUARD+nl+
        b"\t\t\t\t\t\t\t\tvpd131_claim=s;"+nl+b"#endif",1)
    source=source.replace(DRAW,DRAW+nl+b"#ifdef "+GUARD+nl+
        b"\t\t\t\t\t\tif(oamcount>=2) "+HOOK+
        b"sl,rasterpos,oamcount,"+
        b"oams[renderslot][0][0],oams[renderslot][0][1],"+
        b"oams[renderslot][0][2],oams[renderslot][0][3],"+
        b"oams[renderslot][1][0],oams[renderslot][1][1],"+
        b"oams[renderslot][1][2],oams[renderslot][1][3],"+
        b"vpd131_seen0,vpd131_pat0,vpd131_seen1,vpd131_pat1,"+
        b"vpd131_claim,pixel & 3,pixelcolor,PPU_status,*ptr,"+
        b"bgdata.main[bgtile].vpd_stage119_ntaddr);"+nl+b"#endif",1)
    if source.count(HOOK)!=1 or source.count(GUARD)!=4:
        raise ValueError("Incomplete dual-sprite raster instrumentation")
    return source


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("stage129_cpp",type=Path)
    cli.add_argument("stage131_cpp",type=Path)
    args=cli.parse_args()
    if args.stage129_cpp.resolve()==args.stage131_cpp.resolve():
        cli.error("In-place source patch prohibited")
    patched=patch(args.stage129_cpp.read_bytes())
    args.stage131_cpp.parent.mkdir(parents=True,exist_ok=True)
    args.stage131_cpp.write_bytes(patched)
    print("Stage131 pinned newppu dual-OAM sprite priority hook installed")
