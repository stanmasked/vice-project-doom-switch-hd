#!/usr/bin/env python3
"""Stage133 guarded pinned FCEUX sprite CHR fetch and XBuf flip injection."""
import argparse
from pathlib import Path

GUARD=b"VPD_NATIVE_SYNTHETIC_SPRITE_FLIPS"
FETCH=b"oam[5] = CALL_PPUREAD(RefreshAddr);"
DRAW=b"*ptr = PaletteAdjustPixel(pixelcolor);"
HOOK=b"vpd_ppu_probe::stage133_pixel("


def patch(data):
    if not isinstance(data,bytes):
        raise TypeError("Pinned FCEUX source bytes required")
    if GUARD in data or HOOK in data:
        raise ValueError("Duplicate Stage133 observation")
    for anchor in (FETCH,DRAW,b"vpd_ppu_probe::stage131_pixel(",
                   b"vpd_stage129_read",b"vpd_stage119_ntaddr = NTRefreshAddr"):
        if data.count(anchor)!=1 and anchor!=b"vpd_stage129_read":
            raise ValueError("Missing or ambiguous pinned FCEUX raster site")
        if anchor==b"vpd_stage129_read" and data.count(anchor)<2:
            raise ValueError("Stage129 sprite pattern witness unavailable")
    if b"\r\n" in data and data.count(b"\r\n") != data.count(b"\n"):
        raise ValueError("Mixed pinned FCEUX line endings")
    nl=b"\r\n" if b"\r\n" in data else b"\n"
    fetch=(FETCH+nl+b"#ifdef "+GUARD+nl+
           b"\t\t\t\tif(s==0) vpd_ppu_probe::stage133_fetch("+
           b"scanslot,oam[6],line,patternAddress,oam[4],oam[5],oam[2]);"+
           nl+b"#endif")
    draw=(DRAW+nl+b"#ifdef "+GUARD+nl+
          b"\t\t\t\t\t\t"+HOOK+
          b"sl,rasterpos,renderslot,"+
          b"oams[renderslot][0][1],oams[renderslot][0][2],"+
          b"oams[renderslot][0][3],"+
          b"vpd_stage129_read,vpd_stage129_pattern,"+
          b"pixelcolor,*ptr,bgdata.main[bgtile].vpd_stage119_ntaddr);"+
          nl+b"#endif")
    result=data.replace(FETCH,fetch,1).replace(DRAW,draw,1)
    if result.count(GUARD)!=2 or result.count(HOOK)!=1:
        raise ValueError("Stage133 source observer incomplete")
    return result


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("stage131_cpp",type=Path)
    cli.add_argument("stage133_cpp",type=Path)
    args=cli.parse_args()
    if args.stage131_cpp.resolve()==args.stage133_cpp.resolve():
        cli.error("In-place patch not permitted")
    updated=patch(args.stage131_cpp.read_bytes())
    args.stage133_cpp.parent.mkdir(parents=True,exist_ok=True)
    args.stage133_cpp.write_bytes(updated)
    print("Stage133 actual sprite CHR source row, flips and XBuf hooked")
