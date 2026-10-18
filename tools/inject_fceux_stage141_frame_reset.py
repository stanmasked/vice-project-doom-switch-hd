#!/usr/bin/env python3
"""Stage141 guarded pinned-FCEUX pre-render PPU status reset and XBuf."""
import argparse
from pathlib import Path

GUARD=b"VPD_NATIVE_SYNTHETIC_OVERFLOW_FRAME_RESET"
RESET=b"PPU_status = 0;"
EVAL=b"oamcounts[scanslot] = oamcount;"
DRAW=b"*ptr = PaletteAdjustPixel(pixelcolor);"


def patch(source):
    if not isinstance(source,bytes):
        raise TypeError("Pinned C++ source must be raw bytes")
    if GUARD in source or b"vpd_ppu_probe::stage141_before_reset(" in source:
        raise ValueError("Duplicate Stage141 instrumentation")
    for anchor in (RESET,EVAL,DRAW,
                   b"vpd_ppu_probe::stage139_eval(",
                   b"vpd_ppu_probe::stage139_pixel("):
        if source.count(anchor)!=1:
            raise ValueError("Missing or ambiguous pinned newppu site: "+repr(anchor))
    if b"\r\n" in source and source.count(b"\r\n")!=source.count(b"\n"):
        raise ValueError("Mixed source newline formatting")
    nl=b"\r\n" if b"\r\n" in source else b"\n"
    reset=(b"#ifdef "+GUARD+nl+
           b"\t\tvpd_ppu_probe::stage141_before_reset(PPU_status);"+nl+
           b"#endif"+nl+RESET+nl+b"#ifdef "+GUARD+nl+
           b"\t\tvpd_ppu_probe::stage141_after_reset(PPU_status);"+nl+
           b"#endif")
    evaluation=(EVAL+nl+b"#ifdef "+GUARD+nl+
                b"\t\t\tif(oamcount==8 && yp==124) "+
                b"vpd_ppu_probe::stage141_eval("
                b"yp,oamcount,PPU_status,SPRAM[32],SPRAM[35],"+
                b",".join(b"oams[scanslot][%d][6]"%i for i in range(8))+
                b");"+nl+b"#endif")
    draw=(DRAW+nl+b"#ifdef "+GUARD+nl+
          b"\t\t\t\t\t\tvpd_ppu_probe::stage141_pixel("
          b"sl,rasterpos,oamcounts[renderslot],"
          b"PPU_status,*ptr,Sprite16);"+nl+b"#endif")
    output=source.replace(RESET,reset,1).replace(EVAL,evaluation,1)
    output=output.replace(DRAW,draw,1)
    if output.count(GUARD)!=4:
        # before/after reset + OAM evaluation + final raster XBuf.
        raise ValueError("Stage141 reset/selection/XBuf hooks incomplete")
    for marker in (b"vpd_ppu_probe::stage141_before_reset(",
                   b"vpd_ppu_probe::stage141_after_reset(",
                   b"vpd_ppu_probe::stage141_eval(",
                   b"vpd_ppu_probe::stage141_pixel("):
        if output.count(marker)!=1:
            raise ValueError("Missing Stage141 hook")
    return output


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source_cpp",type=Path)
    cli.add_argument("patched_cpp",type=Path)
    args=cli.parse_args()
    if args.source_cpp.resolve()==args.patched_cpp.resolve():
        cli.error("In-place source mutation forbidden")
    output=patch(args.source_cpp.read_bytes())
    args.patched_cpp.parent.mkdir(parents=True,exist_ok=True)
    args.patched_cpp.write_bytes(output)
    print("Stage141 pinned native pre-render status reset, OAM and XBuf hooked")
