#!/usr/bin/env python3
"""Generate 4 transparent RGBA decor frames from original shapes only.

0/1 neon signal (bright/dim); 2/3 rotating fan (two phases).
ROM-free reproducible art, suitable for host CI and Switch NRO builds.
"""
import argparse
import struct
import zlib
from pathlib import Path

FW,FH,COUNT=24,32,4
WIDTH=FW*COUNT
PIXELS=bytearray(WIDTH*FH*4)

def put(frame,x,y,color):
    if 0<=frame<COUNT and 0<=x<FW and 0<=y<FH:
        i=(y*WIDTH+frame*FW+x)*4
        PIXELS[i:i+4]=bytes(color)

def rect(frame,x,y,w,h,color):
    for yy in range(max(0,y),min(FH,y+h)):
        for xx in range(max(0,x),min(FW,x+w)):
            put(frame,xx,yy,color)

for f in range(2):
    # Freestanding industrial warning lamp, bright and dim poses.
    rect(f,10,0,4,32,(45,53,73,255))
    rect(f,7,24,10,3,(87,99,117,255))
    rect(f,3,9,18,14,(30,48,69,230))
    rect(f,5,11,14,10,(79,96,108,255))
    lit=(255,193,93,250) if f==0 else (102,128,163,205)
    rect(f,7,13,10,6,lit)
    rect(f,8,14,8,1,(255,237,187,255) if f==0 else (153,178,190,190))
    rect(f,2,10,2,12,(30,42,65,255))
    rect(f,20,10,2,12,(30,42,65,255))
    if f==0:
        rect(f,5,7,14,2,(255,188,98,130))
        rect(f,7,5,10,2,(255,188,98,65))
for f in (2,3):
    # Grille + alternating fan blades, transparent outside silhouette.
    rect(f,5,3,14,2,(93,114,133,255))
    rect(f,5,26,14,2,(93,114,133,255))
    rect(f,3,5,2,21,(79,94,118,255))
    rect(f,19,5,2,21,(79,94,118,255))
    rect(f,6,6,12,19,(24,39,60,245))
    for x in (7,10,13,16):
        rect(f,x,7,1,17,(72,95,121,170))
    for y in (9,14,19,23):
        rect(f,6,y,12,1,(90,115,137,195))
    if f==2:
        rect(f,10,8,4,7,(157,202,207,255))
        rect(f,10,17,4,7,(157,202,207,255))
        rect(f,6,14,6,3,(157,202,207,255))
        rect(f,13,14,6,3,(157,202,207,255))
    else:
        for y,x in ((8,7),(8,14),(19,7),(19,14)):
            rect(f,x,y,4,5,(160,204,213,255))
    rect(f,11,14,2,3,(247,195,95,255))

BODY=bytes(PIXELS)
VPAT=b'VPAT'+struct.pack('<7H',1,WIDTH,FH,FW,FH,COUNT,0)
VPAT+=struct.pack('<I',zlib.crc32(BODY)&0xffffffff)+BODY

def make_header():
    lines=['    '+', '.join('0x%02x'%x for x in VPAT[i:i+20])+','
           for i in range(0,len(VPAT),20)]
    return ('#pragma once\n#include <cstddef>\nnamespace vpd_decor {\n'
            'inline constexpr unsigned char kAtlasBlob[] = {\n'
            +'\n'.join(lines)+'\n};\n'
            'inline constexpr std::size_t kAtlasBytes=sizeof(kAtlasBlob);\n}\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('header',type=Path)
    parser.add_argument('--raw',type=Path)
    parser.add_argument('--preview',type=Path)
    args=parser.parse_args()
    args.header.parent.mkdir(parents=True,exist_ok=True)
    args.header.write_text(make_header(),encoding='utf8')
    if args.raw:
        args.raw.parent.mkdir(parents=True,exist_ok=True)
        args.raw.write_bytes(VPAT)
    if args.preview:
        args.preview.parent.mkdir(parents=True,exist_ok=True)
        with args.preview.open('wb') as f:
            f.write(f'P6\n{WIDTH*4} {FH*4}\n255\n'.encode())
            for y in range(FH):
                row=bytearray()
                for x in range(WIDTH):
                    i=(y*WIDTH+x)*4
                    alpha=BODY[i+3]
                    rgb=bytes((BODY[i+k]*alpha+26*(255-alpha)+127)//255
                              for k in range(3))
                    row.extend(rgb*4)
                for _ in range(4):
                    f.write(row)
    print(f'Decor VPAT: {WIDTH}x{FH}, 4 frames; {len(VPAT)} bytes')

if __name__=='__main__':
    main()
