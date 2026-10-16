#!/usr/bin/env python3
"""Static OAM sprite preview using a privately captured NES PPU and RAM snapshot.

The preview is not an emulator frame: scrolling, scanline CHR swaps, sprite
overflow and NTSC/PPU timing are not simulated. Captured files remain private.
"""
import argparse
import json
from pathlib import Path
from PIL import Image
from render_ppu_snapshot import NES_RGB, load_snapshot, render_background, palette_color

def observed_ppuctrl(meta):
    try:
        ctrl = int(meta.get('ppuctrl','unknown'),16)
    except ValueError:
        return None
    if not 0 <= ctrl <= 255:
        raise ValueError('PPUCTRL byte out of range')
    return ctrl

def _background_opaque(ppu,nametable,x,y,pattern_base):
    tile=ppu[0x2000+0x400*nametable+(y//8)*32+(x//8)]
    off=pattern_base+tile*16+y%8
    bit=7-x%8
    return ((ppu[off]>>bit)&1)|(((ppu[off+8]>>bit)&1)<<1)

def sprite_pixel(ppu,tile,px,py,height,sprite_pattern_base):
    if len(ppu)!=0x4000:raise ValueError('PPU snapshot must be 16KiB')
    if not 0<=tile<=255 or not 0<=px<8 or not 0<=py<height:
        raise ValueError('Sprite tile/pixel coordinates invalid')
    if height not in (8,16):raise ValueError('NES sprite height must be 8 or 16')
    if sprite_pattern_base not in (0,0x1000):
        raise ValueError('Sprite pattern base must be 0 or 0x1000')
    if height==16:
        base=(tile&1)*0x1000
        tile=(tile&0xFE)+(py//8)
    else:
        base=sprite_pattern_base
    off=base+tile*16+py%8
    shift=7-px
    return ((ppu[off]>>shift)&1)|(((ppu[off+8]>>shift)&1)<<1)

def overlay_sprites(ppu,ram,nametable=0,bg_pattern_base=0,
                    sprite_height=8,sprite_pattern_base=0,ppumask=None):
    """Composite static OAM source page $0700 over a static unscrolled background."""
    if len(ppu)!=0x4000 or len(ram)!=0x800:
        raise ValueError('Expected PPU 16KiB and CPU RAM 2KiB captures')
    if nametable not in (0,1,2,3) or bg_pattern_base not in (0,0x1000):
        raise ValueError('Invalid nametable/pattern table')
    if sprite_height not in (8,16) or sprite_pattern_base not in (0,0x1000):
        raise ValueError('Invalid sprite size/pattern table')
    if ppumask is not None and not 0<=ppumask<=255:
        raise ValueError('PPUMASK outside byte range')
    image=render_background(ppu,nametable,bg_pattern_base,scale=1)
    if ppumask is not None and not (ppumask&0x10):
        return image
    pixels=image.load()
    # Descending OAM order approximates lower-index sprite priority.
    for index in range(63,-1,-1):
        top_byte,tile,attr,x=ram[0x700+index*4:0x704+index*4]
        top=(top_byte+1)&255
        for sy in range(sprite_height):
            screen_y=top+sy
            if not 0<=screen_y<240:continue
            for sx in range(8):
                screen_x=x+sx
                if screen_x>=256:continue
                if ppumask is not None and screen_x<8 and not (ppumask&0x04):
                    continue
                source_x=7-sx if attr&0x40 else sx
                source_y=sprite_height-1-sy if attr&0x80 else sy
                value=sprite_pixel(ppu,tile,source_x,source_y,
                                   sprite_height,sprite_pattern_base)
                if value==0:continue
                if attr&0x20 and _background_opaque(
                    ppu,nametable,screen_x,screen_y,bg_pattern_base):
                    continue
                slot=0x11+4*(attr&3)+value-1
                pixels[screen_x,screen_y]=NES_RGB[palette_color(ppu,slot)]
    return image

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture_prefix',type=Path)
    parser.add_argument('--out',type=Path,default=Path('private/preview/oam_composite.png'))
    parser.add_argument('--nametable',type=int,choices=[0,1,2,3],default=0)
    parser.add_argument('--bg-pattern-base',choices=['auto','0x0000','0x1000'],default='auto')
    parser.add_argument('--sprite-pattern-base',choices=['auto','0x0000','0x1000'],default='auto')
    parser.add_argument('--sprite-height',choices=['auto','8','16'],default='auto')
    parser.add_argument('--scale',type=int,default=2)
    args=parser.parse_args()
    ppu,ram,meta=load_snapshot(args.capture_prefix)
    if ram is None:
        parser.error('Missing .ram.bin: OAM source requires captured CPU RAM')
    ctrl=observed_ppuctrl(meta)
    if ctrl is None and 'auto' in (args.bg_pattern_base,args.sprite_pattern_base,args.sprite_height):
        parser.error('PPUCTRL is unknown: specify both pattern bases and sprite height')
    bg=(0x1000 if ctrl&0x10 else 0) if args.bg_pattern_base=='auto' else int(args.bg_pattern_base,16)
    sprite=(0x1000 if ctrl&0x08 else 0) if args.sprite_pattern_base=='auto' else int(args.sprite_pattern_base,16)
    height=(16 if ctrl&0x20 else 8) if args.sprite_height=='auto' else int(args.sprite_height)
    mask=int(meta['ppumask'],16) if meta.get('ppumask','unknown')!='unknown' else None
    if not 1<=args.scale<=8:parser.error('Scale must be 1..8')
    image=overlay_sprites(ppu,ram,args.nametable,bg,height,sprite,mask)
    if args.scale!=1:
        image=image.resize((256*args.scale,240*args.scale),Image.Resampling.NEAREST)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    image.save(args.out)
    print(json.dumps({'preview':str(args.out),'sprite_height':height,
                      'ppu_ctrl_observed':ctrl is not None,
                      'warning':'Static sprite approximation; not a live NES frame or validated original level'},indent=2))

if __name__=='__main__':main()
