#!/usr/bin/env python3
"""Build a PRIVATE contact-sheet PNG from validated local FCEUX screenshots.

This program never uploads ROM, FM2, screenshots or game graphics.
The generated image contains copyrighted source-game pixels: keep it private.
"""
import argparse
import json
from pathlib import Path
import struct
import zlib
from audit_private_fceux_storyboard import audit, P6_HEADER, WIDTH, HEIGHT

DIGITS={
 '0':('111','101','101','101','111'),
 '1':('010','110','010','010','111'),
 '2':('111','001','111','100','111'),
 '3':('111','001','111','001','111'),
 '4':('101','101','111','001','001'),
 '5':('111','100','111','001','111'),
 '6':('111','100','111','101','111'),
 '7':('111','001','010','010','010'),
 '8':('111','101','111','101','111'),
 '9':('111','101','111','001','111')
}

def chunk(name,data):
    return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)

def make_sheet(root,out,*,columns=5,require_complete=True):
    root=Path(root)
    out=Path(out)
    if not 1<=columns<=8:
        raise ValueError('contact sheet columns must be 1..8')
    if out.is_symlink() or out.exists():
        raise ValueError('refusing to overwrite contact-sheet destination')
    if not out.parent.is_dir():
        raise ValueError('contact-sheet parent directory does not exist')
    if root.resolve()==out.parent.resolve():
        raise ValueError('contact sheet must be outside strict capture directory')
    report=audit(root,require_complete=require_complete)
    names=sorted(root.glob('frame_*.meta.txt'),key=lambda p:(len(p.name),p.name))
    frames=[int(p.name[6:-9]) for p in names]
    screenshots=[]
    for frame in frames:
        path=root/('frame_'+format(frame,'06d')+'.ppm')
        raw=path.read_bytes()
        assert raw.startswith(P6_HEADER)
        screenshots.append(raw[len(P6_HEADER):])
    count=len(frames)
    nrows=(count+columns-1)//columns
    banner=16
    width=WIDTH*columns
    height=(HEIGHT+banner)*nrows
    background=bytes((26,30,37))
    image=bytearray(background*(width*height))
    for i,(frame,raw) in enumerate(zip(frames,screenshots)):
        origin_x=(i%columns)*WIDTH
        origin_y=(i//columns)*(HEIGHT+banner)
        for j,glyph in enumerate(str(frame)):
            for y,line in enumerate(DIGITS[glyph]):
                for x,bit in enumerate(line):
                    if bit=='1':
                        for dy in range(2):
                            for dx in range(2):
                                yy=origin_y+2+y*2+dy
                                xx=origin_x+5+j*8+x*2+dx
                                pos=(yy*width+xx)*3
                                image[pos:pos+3]=b'\xf7\xf7\xf7'
        for y in range(HEIGHT):
            start=((origin_y+banner+y)*width+origin_x)*3
            image[start:start+WIDTH*3]=raw[y*WIDTH*3:(y+1)*WIDTH*3]
    png=b'\x89PNG\r\n\x1a\n'
    png+=chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))
    rows=b''.join(b'\x00'+image[y*width*3:(y+1)*width*3] for y in range(height))
    png+=chunk(b'IDAT',zlib.compress(rows,6))+chunk(b'IEND',b'')
    with out.open('xb') as f:
        f.write(png)
    return {'output':'private contact sheet PNG, derived from locally owned content',
            'sample_count':count,'frame_numbers':frames,
            'width':width,'height':height,'columns':columns,
            'complete_window_verified':report['complete_window_verified'],
            'source_gameplay_verified':False,
            'original_stage_identity_proven':False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('private_storyboard',type=Path)
    p.add_argument('private_output_png',type=Path)
    p.add_argument('--columns',type=int,default=5)
    p.add_argument('--allow-partial',action='store_true',
                   help='allow visually exploring an incomplete checkpoint set')
    args=p.parse_args()
    try:
        summary=make_sheet(args.private_storyboard,args.private_output_png,
                           columns=args.columns,require_complete=not args.allow_partial)
    except (OSError,ValueError,UnicodeError) as exc:
        p.exit(1,'PRIVATE_CONTACT_SHEET_INCONCLUSIVE: '+str(exc)+'\n')
    print('PRIVATE_FCEUX_CONTACT_SHEET_PASS')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    main()
