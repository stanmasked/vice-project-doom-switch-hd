#!/usr/bin/env python3
"""Stage149: instrument actual pinned FCEUX newppu $2002/$2003/$2004 paths.

Runs after the existing Stage141 patched PPU source. No original ROM
contents and no private framebuffer buffers are copied or published.
"""
import argparse
from pathlib import Path

INCLUDE=b'#include "vpd_newppu_raw_step_probe.h"'
EXTRA=b'#include "vpd_stage149_cpu_oam_probe.h"'
READ=b"\t\t\t(PPU_status & 0x80) != 0);"
ADDR=b"\tPPUSPL = V & 0x7;"
OAM_ENTRY=b"static DECLFW(B2004) {"
OAM_MASK=b"\t\t\tV &= 0xE3;"
DATA=(b"\t\tSPRAM[PPU[3]] = V;"
      b"\n\t\tPPU[3] = (PPU[3] + 1) & 0xFF;")
GUARD=b"VPD_NATIVE_SYNTHETIC_OAM_CPU_WRITES"


def patch(source):
    if not isinstance(source,bytes):
        raise TypeError("Expected pinned newppu C++ source bytes")
    if GUARD in source or EXTRA in source:
        raise ValueError("Already patched Stage149 register instrumentation")
    if b"\r\n" in source and source.count(b"\r\n")!=source.count(b"\n"):
        raise ValueError("Mixed FCEUX line endings")
    nl=b"\r\n" if b"\r\n" in source else b"\n"
    for marker in (INCLUDE,READ,ADDR,
                   b"static DECLFR(A2002) {",
                   b"static DECLFW(B2003) {",
                   b"static DECLFW(B2004) {",
                   b"vpd_ppu_probe::stage141_pixel("):
        if source.count(marker)!=1:
            raise ValueError("Missing/ambiguous pinned register hook "+repr(marker))
    normalized=source.replace(b"\r\n",b"\n")
    if normalized.count(DATA)!=1:
        raise ValueError("Cannot isolate pinned newppu OAM auto-increment write")
    # The Stage103 CPU read observer is already inserted in the actual
    # A2002 branch; a high return from BIT $2002 clears PPU_status bit7,
    # so save the returned flag BEFORE later CPU-side OAM writes.
    begin=source.index(b"static DECLFR(A2002) {")
    end=source.index(b"static DECLFR(A2004) {")
    if not begin<source.index(READ)<end:
        raise ValueError("Stage103 source read anchor outside A2002")
    a2003=source.index(b"static DECLFW(B2003) {")
    a2004=source.index(b"static DECLFW(B2004) {")
    a2005=source.index(b"static DECLFW(B2005) {")
    if not a2003<source.index(ADDR)<a2004:
        raise ValueError("OAMADDR hook site outside B2003")
    data_source=DATA.replace(b"\n",nl)
    if not a2004<source.index(data_source)<a2005:
        raise ValueError("OAMDATA newppu hook site outside B2004")
    if (source.count(OAM_MASK)!=1 or
            not a2004<source.index(OAM_MASK)<source.index(data_source)):
        raise ValueError("Expected newppu attribute mask before raw-to-stored OAM write")
    if (source.count(b"if ((PPU[3] & 3) == 2)")!=1 or
            not a2004<source.index(b"if ((PPU[3] & 3) == 2)")<
            source.index(OAM_MASK)):
        raise ValueError("Pinned $2004 attribute mask condition changed")

    include=(INCLUDE+nl+b"#ifdef "+GUARD+nl+
             EXTRA+nl+b"#endif")
    read=(READ+nl+b"#ifdef "+GUARD+nl+
          b"\t\tif(newppu) vpd_ppu_probe::stage149_status_read("+
          b"(ret & 0x80)!=0);"+nl+b"#endif")
    address=(ADDR+nl+b"#ifdef "+GUARD+nl+
             b"\tvpd_ppu_probe::stage149_oam_address("+
             b"V,PPU[3],newppu);"+nl+b"#endif")
    # Capture CPU-supplied V at the ENTRY to B2004, before FCEUX
    # masks unconnected sprite attribute bits with V &= 0xE3.
    entry=(OAM_ENTRY+nl+b"#ifdef "+GUARD+nl+
           b"\tconst unsigned vpd149_cpu_value = V;"+nl+b"#endif")
    data=(b"\t\tSPRAM[PPU[3]] = V;"+nl+
          b"#ifdef "+GUARD+nl+
          b"\t\tvpd_ppu_probe::stage149_oam_data("+
          b"PPU[3],vpd149_cpu_value,SPRAM[PPU[3]],newppu);"+nl+
          b"#endif"+nl+
          b"\t\tPPU[3] = (PPU[3] + 1) & 0xFF;")
    output=source.replace(INCLUDE,include,1)
    output=output.replace(READ,read,1)
    output=output.replace(ADDR,address,1)
    output=output.replace(OAM_ENTRY,entry,1)
    output=output.replace(data_source,data,1)
    if (output.count(GUARD)!=5 or
        output.count(b"vpd_ppu_probe::stage149_status_read(")!=1 or
        output.count(b"vpd_ppu_probe::stage149_oam_address(")!=1 or
        output.count(b"vpd_ppu_probe::stage149_oam_data(")!=1 or
        output.count(b"const unsigned vpd149_cpu_value = V;")!=1 or
        output.index(b"vpd149_cpu_value = V;")>output.index(OAM_MASK)):
        raise ValueError("Stage149 native CPU register hooks incomplete")
    return output


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source_cpp",type=Path)
    cli.add_argument("patched_cpp",type=Path)
    args=cli.parse_args()
    if args.source_cpp.resolve()==args.patched_cpp.resolve():
        cli.error("Cannot modify input FCEUX PPU source in-place")
    source=patch(args.source_cpp.read_bytes())
    args.patched_cpp.parent.mkdir(parents=True,exist_ok=True)
    args.patched_cpp.write_bytes(source)
    print("Stage149 pinned FCEUX PPU $2002/$2003/$2004 CPU hooks installed")
