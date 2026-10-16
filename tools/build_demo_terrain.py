#!/usr/bin/env python3
"""Build four original 16x16 environmental tiles as a VPAT texture sheet.

Frames: 0 exposed top, 1 internal masonry, 2 left-facing wall,
3 right-facing wall. Entirely synthetic, not NES game artwork.
Pure Python so it works in the devkitPro NRO build container.
"""
import argparse
import struct
import zlib
from pathlib import Path

SIDE=16
FRAMES=4
WIDTH=SIDE*FRAMES
HEIGHT=SIDE
RGBA=bytearray(WIDTH*HEIGHT*4)

def dot(frame,x,y,color):
    if 0<=frame<FRAMES and 0<=x<SIDE and 0<=y<SIDE:
        offset=(y*WIDTH+frame*SIDE+x)*4
        RGBA[offset:offset+4]=bytes((*color,255))

def rectangle(frame,x,y,w,h,color):
    for yy in range(max(0,y),min(SIDE,y+h)):
        for xx in range(max(0,x),min(SIDE,x+w)):
            dot(frame,xx,yy,color)

BASE=(42,49,68)
DARK=(29,36,55)
MID=(61,75,92)
LIGHT=(96,123,138)
BLUE=(71,173,184)
GLOW=(137,215,198)

for frame in range(FRAMES):
    rectangle(frame,0,0,16,16,BASE)
    # Steel/stone masonry and tiny irregular seams: all opaque.
    rectangle(frame,0,6,16,1,DARK)
    rectangle(frame,0,13,16,1,DARK)
    rectangle(frame,8,7,1,6,DARK)
    rectangle(frame,3,14,1,2,DARK)
    rectangle(frame,13,0,1,6,DARK)
    rectangle(frame,2,2,3,1,MID)
    rectangle(frame,10,10,4,1,MID)
    rectangle(frame,3,8,2,1,LIGHT)
    rectangle(frame,12,3,2,1,LIGHT)
    if frame==0:
        rectangle(frame,0,0,16,2,GLOW)
        rectangle(frame,0,2,16,2,BLUE)
        rectangle(frame,0,4,16,1,(46,106,125))
        rectangle(frame,1,9,5,1,(55,82,97))
        rectangle(frame,11,12,4,1,(55,82,97))
    elif frame==1:
        rectangle(frame,2,3,10,1,MID)
        rectangle(frame,4,9,7,1,(55,80,96))
        rectangle(frame,0,0,16,1,(57,67,89))
    elif frame==2:
        rectangle(frame,0,0,2,16,GLOW)
        rectangle(frame,2,0,2,16,BLUE)
        rectangle(frame,4,0,1,16,(39,106,123))
        rectangle(frame,6,3,5,1,MID)
    else:
        rectangle(frame,14,0,2,16,GLOW)
        rectangle(frame,12,0,2,16,BLUE)
        rectangle(frame,11,0,1,16,(39,106,123))
        rectangle(frame,5,8,5,1,MID)

DATA=bytes(RGBA)
CRC=zlib.crc32(DATA)&0xffffffff
VPAT=b'VPAT'+struct.pack('<7H',1,WIDTH,HEIGHT,SIDE,SIDE,FRAMES,0)+struct.pack('<I',CRC)+DATA

def header_text(blob):
    chunks=[blob[i:i+20] for i in range(0,len(blob),20)]
    lines=['    '+', '.join('0x%02x'%value for value in row)+',' for row in chunks]
    return ('#pragma once\n#include <cstddef>\nnamespace vpd_terrain {\n'
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
    args.header.write_text(header_text(VPAT),encoding='utf8')
    if args.raw:
        args.raw.parent.mkdir(parents=True,exist_ok=True)
        args.raw.write_bytes(VPAT)
    if args.preview:
        args.preview.parent.mkdir(parents=True,exist_ok=True)
        with args.preview.open('wb') as target:
            target.write(f'P6\n{WIDTH*6} {HEIGHT*6}\n255\n'.encode('ascii'))
            for y in range(HEIGHT):
                row=bytearray()
                for x in range(WIDTH):
                    index=(y*WIDTH+x)*4
                    row.extend(DATA[index:index+3]*6)
                for _ in range(6):target.write(row)
    print(f'Terrain VPAT v1: {WIDTH}x{HEIGHT}, {FRAMES} frames, '
          f'{len(VPAT)} bytes, crc={CRC:08x}')

if __name__=='__main__':
    main()
