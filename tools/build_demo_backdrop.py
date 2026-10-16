#!/usr/bin/env python3
"""Generate original ROM-free two-layer skyline VPAT: 128x96 x 2 frames.

Far and near silhouettes are independent, drawn procedurally. The resulting
binary is source-free test artwork, not extracted Nintendo Entertainment
System content. Pure Python, to run in devkitPro CI.
"""
import argparse
import struct
import zlib
from pathlib import Path

W,H,COUNT=128,96,2
TOTAL_WIDTH=W*COUNT
pixels=bytearray(TOTAL_WIDTH*H*4)

def setpixel(frame,x,y,color):
    if 0<=frame<COUNT and 0<=x<W and 0<=y<H:
        i=(y*TOTAL_WIDTH+frame*W+x)*4
        pixels[i:i+4]=bytes(color)

def rect(frame,x,y,wide,tall,color):
    for yy in range(max(0,y),min(H,y+tall)):
        for xx in range(max(0,x),min(W,x+wide)):
            setpixel(frame,xx,yy,color)

def hash32(n):
    n=(n^(n>>16))*0x7feb352d&0xffffffff
    n=(n^(n>>15))*0x846ca68b&0xffffffff
    return n^(n>>16)

for layer in range(COUNT):
    # Different height curves and window colors distinguish the 2 depths.
    gap=10 if layer==0 else 12
    for building in range(W//gap+2):
        seed=hash32(building*71+layer*927+19)
        x=building*gap-(3 if layer else 0)
        top=(47+seed%27) if layer==0 else (29+seed%36)
        base=(43,54,81,255) if layer==0 else (29,40,66,255)
        lit=(99,118,146,255) if layer==0 else (172,133,117,255)
        window=(76,83,127,255) if layer==0 else (170,102,87,255)
        rect(layer,x,top,gap-1,H-top,base)
        rect(layer,x+2,top-3,1,3,base)
        for y in range(top+5,H-5,11):
            for xx in range(x+2,x+gap-2,4):
                if hash32(seed+(xx+3)*17+y*5)%5<2:
                    rect(layer,xx,y,2,3,lit)
        if layer==1:
            rect(layer,x,top,gap-1,1,window)
    rect(layer,0,H-5,W,5,(36,47,73,255) if layer==0
         else (25,32,52,255))
    # A few architectural accents ensure a useful alpha silhouette.
    for x in range(14+layer*12,W,47):
        top=18 if layer==0 else 9
        rect(layer,x,top,2,36,(50,64,91,255) if layer==0
             else (61,66,94,255))
        rect(layer,x-3,top+9,8,1,(119,119,144,255))

PAYLOAD=bytes(pixels)
CRC=zlib.crc32(PAYLOAD)&0xffffffff
ATLAS=b"VPAT"+struct.pack("<7H",1,TOTAL_WIDTH,H,W,H,COUNT,0)+struct.pack("<I",CRC)+PAYLOAD

def make_header():
    parts=[ATLAS[i:i+20] for i in range(0,len(ATLAS),20)]
    rows=["    "+", ".join("0x%02x"%v for v in part)+"," for part in parts]
    return ("#pragma once\n#include <cstddef>\nnamespace vpd_backdrop {\n"
            "inline constexpr unsigned char kAtlasBlob[] = {\n"+
            "\n".join(rows)+"\n};\n"
            "inline constexpr std::size_t kAtlasBytes=sizeof(kAtlasBlob);\n}\n")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("header",type=Path)
    p.add_argument("--raw",type=Path)
    p.add_argument("--preview",type=Path)
    args=p.parse_args()
    args.header.parent.mkdir(parents=True,exist_ok=True)
    args.header.write_text(make_header(),encoding="utf8")
    if args.raw:
        args.raw.parent.mkdir(parents=True,exist_ok=True)
        args.raw.write_bytes(ATLAS)
    if args.preview:
        args.preview.parent.mkdir(parents=True,exist_ok=True)
        with args.preview.open("wb") as f:
            f.write(f"P6\n{TOTAL_WIDTH*2} {H*2}\n255\n".encode())
            for y in range(H):
                row=bytearray()
                for x in range(TOTAL_WIDTH):
                    i=(y*TOTAL_WIDTH+x)*4
                    alpha=PAYLOAD[i+3]
                    color=tuple((PAYLOAD[i+c]*alpha+20*(255-alpha)+127)//255
                                for c in range(3))
                    row.extend(bytes(color)*2)
                f.write(row)
                f.write(row)
    print(f"Backdrop VPAT: {TOTAL_WIDTH}x{H} / 2 layers, {len(ATLAS)} bytes, CRC {CRC:08x}")

if __name__=="__main__":
    main()
