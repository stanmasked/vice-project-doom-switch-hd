#!/usr/bin/env python3
"""Create an original ROM-free animated 4-frame RGBA hero atlas as a C++ header.

VPAT v1 layout (little endian): 4-byte magic VPAT, u16 version,
u16 width/height, u16 frame width/height/count/flags, u32 CRC32 of pixels,
then row-major straight RGBA8888. Does not use NES or extracted graphics.
"""
import argparse
import struct
import zlib
from pathlib import Path

FW,FH,COUNT=24,32,4
WIDTH,HEIGHT=FW*COUNT,FH
P=bytearray(WIDTH*HEIGHT*4)

def pixel(frame,x,y,rgb,alpha=255):
    if not (0<=frame<COUNT and 0<=x<FW and 0<=y<FH):return
    idx=((y*WIDTH)+frame*FW+x)*4
    P[idx:idx+4]=bytes((*rgb,alpha))

def box(frame,x,y,w,h,color,alpha=255):
    for py in range(max(0,y),min(FH,y+h)):
        for px in range(max(0,x),min(FW,x+w)):
            pixel(frame,px,py,color,alpha)

for fr in range(COUNT):
    hop=fr==3
    walk=fr in (1,2)
    stride=2 if fr==1 else -2 if fr==2 else 0
    bob=-3 if hop else (fr%2 if walk else 0)
    # Foot/leg movement: four authored animation poses.
    box(fr,8+stride,22+bob,4,8,(41,48,72))
    box(fr,14-stride,22+bob,4,8,(41,48,72))
    box(fr,7+stride,29+bob,7,2,(24,29,49))
    box(fr,13-stride,29+bob,7,2,(24,29,49))
    box(fr,6,12+bob,14,12,(164,51,68))
    box(fr,8,15+bob,10,5,(218,91,91))
    box(fr,9,3+bob,12,12,(220,179,137))
    box(fr,8,2+bob,13,6,(52,43,56))
    box(fr,18,9+bob,2,2,(29,32,49))
    arm_y=12+bob-3 if hop else 13+bob
    box(fr,3,arm_y,4,8,(216,162,118))
    box(fr,20,arm_y,4,8,(216,162,118))
    box(fr,21,arm_y+3,3,9,(111,136,153))
    box(fr,20,arm_y+11,5,2,(224,232,234))
    # An alpha-128 halo can test the straight-alpha blending path.
    box(fr,2,15+bob,1,3,(238,174,89),128)

payload=bytes(P)
header=b'VPAT'+struct.pack('<7H',1,WIDTH,HEIGHT,FW,FH,COUNT,0)+struct.pack('<I',zlib.crc32(payload)&0xffffffff)
blob=header+payload

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('header',type=Path)
    p.add_argument('--raw',type=Path)
    p.add_argument('--preview',type=Path)
    args=p.parse_args()
    args.header.parent.mkdir(parents=True,exist_ok=True)
    rows=[]
    for i in range(0,len(blob),20):
        rows.append('    '+', '.join('0x%02x'%b for b in blob[i:i+20])+',')
    args.header.write_text('#pragma once\n#include <cstddef>\n'
       'namespace vpd_demo {\ninline constexpr unsigned char kAtlasBlob[] = {\n'
       +'\n'.join(rows)+'\n};\n'
       'inline constexpr std::size_t kAtlasBytes=sizeof(kAtlasBlob);\n}\n',encoding='utf8')
    if args.raw:
        args.raw.parent.mkdir(parents=True,exist_ok=True)
        args.raw.write_bytes(blob)
    if args.preview:
        args.preview.parent.mkdir(parents=True,exist_ok=True)
        bg=(24,27,49)
        with args.preview.open('wb') as f:
            f.write(f'P6\n{WIDTH*4} {HEIGHT*4}\n255\n'.encode('ascii'))
            for y in range(HEIGHT):
                for _ in range(4):
                    for x in range(WIDTH):
                        i=(y*WIDTH+x)*4
                        a=payload[i+3]
                        color=tuple((payload[i+k]*a+bg[k]*(255-a)+127)//255 for k in range(3))
                        f.write(bytes(color)*4)
    print(f'VPAT v1: {WIDTH}x{HEIGHT}, {COUNT} frames, {len(blob)} bytes, CRC32={zlib.crc32(payload):08x}')

if __name__=='__main__':main()
