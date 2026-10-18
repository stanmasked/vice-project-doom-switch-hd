#!/usr/bin/env python3
"""Stage135 guarded live FCEUX 8x16 sprite source row and XBuf hooks."""
import argparse
from pathlib import Path

GUARD=b"VPD_NATIVE_SYNTHETIC_SPRITE_8X16"
FETCH=b"oam[5] = CALL_PPUREAD(RefreshAddr);"
DRAW=b"*ptr = PaletteAdjustPixel(pixelcolor);"
HOOK=b"vpd_ppu_probe::stage135_pixel("

def patch(source):
    if not isinstance(source,bytes):
        raise TypeError("Pinned FCEUX C++ bytes required")
    if GUARD in source or HOOK in source:
        raise ValueError("Duplicate Stage135 native instrument")
    for anchor in (FETCH,DRAW,b"vpd_ppu_probe::stage133_pixel(",
                   b"vpd_stage129_read",b"patternAddress += line & 7;"):
        if anchor==b"vpd_stage129_read":
            if source.count(anchor)<2:
                raise ValueError("Missing prior sprite pattern witness")
        elif source.count(anchor)!=1:
            raise ValueError("Ambiguous real newppu sprite site")
    if b"\r\n" in source and source.count(b"\r\n")!=source.count(b"\n"):
        raise ValueError("Mixed source line endings")
    nl=b"\r\n" if b"\r\n" in source else b"\n"
    fetch=(FETCH+nl+b"#ifdef "+GUARD+nl+
           b"\t\t\t\tif(s==0 && oam[7] && (oam[1]==2 || oam[1]==3) "
           b"&& oam[6]==0) "+
           b"vpd_ppu_probe::stage135_fetch("
           b"scanslot,oam[6],line,patternAddress,oam[4],oam[5],"
           b"oam[2],oam[1],Sprite16);"+nl+b"#endif")
    draw=(DRAW+nl+b"#ifdef "+GUARD+nl+
          b"\t\t\t\t\t\t"+HOOK+
          b"sl,rasterpos,renderslot,oams[renderslot][0][1],"
          b"oams[renderslot][0][2],oams[renderslot][0][3],"
          b"vpd_stage129_read,vpd_stage129_pattern,pixelcolor,*ptr);"+
          nl+b"#endif")
    result=source.replace(FETCH,fetch,1).replace(DRAW,draw,1)
    if result.count(GUARD)!=2 or result.count(HOOK)!=1 or result.count(
        b"vpd_ppu_probe::stage135_fetch(")!=1:
        raise ValueError("Incomplete real FCEUX 8x16 hooks")
    return result

if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("previous_ppu",type=Path)
    cli.add_argument("updated_ppu",type=Path)
    args=cli.parse_args()
    if args.previous_ppu.resolve()==args.updated_ppu.resolve():
        cli.error("In-place source mutation forbidden")
    output=patch(args.previous_ppu.read_bytes())
    args.updated_ppu.parent.mkdir(parents=True,exist_ok=True)
    args.updated_ppu.write_bytes(output)
    print("Stage135 newppu fetched 8x16 tile pair and actual raster XBuf hooked")
