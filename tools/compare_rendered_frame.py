#!/usr/bin/env python3
"""Compare true FCEUX screen palette indices to a static PPU/OAM reconstruction.

This is a diagnostic, NOT proof of authentic screen layout. Only explicit
static normal scroll is supported; midframe scroll splits, CHR bank changes,
sprite overflow, emphasis and precise timing are NOT emulated.
Original-game capture files / frame previews MUST remain local, outside Git.
"""
import argparse
import json
from pathlib import Path
from PIL import Image
from render_ppu_snapshot import load_snapshot
try:
    from render_ppu_snapshot import bg_pixel, palette_color
except ImportError:
    from render_ppu_snapshot import background_color_index as bg_pixel
    from render_ppu_snapshot import nes_palette_index as palette_color
from render_oam_sprites import sprite_pixel
from ppu_scroll import resolve_pixel, scroll_background_pixel, opaque_background_pixel

WIDTH, HEIGHT = 256, 240
PIXELS = WIDTH * HEIGHT

def load_reference(prefix):
    prefix=Path(prefix)
    rgb=Path(str(prefix)+'.screen.rgb.bin').read_bytes()
    pal=Path(str(prefix)+'.screen.pal.bin').read_bytes()
    if len(rgb)!=PIXELS*3:raise ValueError('Expected 184320 RGB bytes from FCEUX')
    if len(pal)!=PIXELS:raise ValueError('Expected 61440 palette-index bytes')
    if any(v>63 and v!=254 for v in pal):
        raise ValueError('Reference contains illegal NES palette indices')
    return rgb,pal

def reconstructed_indices(ppu,ram,nt,base,sprites=False,height=8,
                          sprite_base=0,mask=None,scroll_x=0,scroll_y=0):
    """Produce a palette-index image, not approximate RGB."""
    if len(ppu)!=16384:raise ValueError('Expected 16KiB PPU snapshot')
    if nt not in range(4) or base not in (0,0x1000):
        raise ValueError('Invalid nametable/pattern base')
    if mask is not None and not 0<=mask<=255:
        raise ValueError('Invalid PPUMASK')
    if sprites and (ram is None or len(ram)!=2048):
        raise ValueError('Sprites require 2KiB CPU RAM')
    if sprites and (height not in (8,16) or sprite_base not in (0,0x1000)):
        raise ValueError('Invalid sprite size/pattern table')
    resolve_pixel(nt,0,0,scroll_x,scroll_y)
    bg_enabled=mask is None or bool(mask&0x08)
    left_visible=mask is None or bool(mask&0x02)
    backdrop=palette_color(ppu,0)
    pixels=bytearray(PIXELS)
    opaque=bytearray(PIXELS)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            i=y*WIDTH+x
            visible=bg_enabled and (x>=8 or left_visible)
            pixels[i]=scroll_background_pixel(ppu,nt,x,y,base,scroll_x,scroll_y) if visible else backdrop
            opaque[i]=1 if visible and opaque_background_pixel(ppu,nt,x,y,base,scroll_x,scroll_y) else 0
    if not sprites or (mask is not None and not mask&0x10):
        return bytes(pixels)
    spr_left=mask is None or bool(mask&0x04)
    for n in range(63,-1,-1):
        sy,tile,attributes,sx=ram[0x700+n*4:0x704+n*4]
        top=(sy+1)&255
        for dy in range(height):
            y=top+dy
            if y>=HEIGHT:continue
            source_y=height-1-dy if attributes&0x80 else dy
            for dx in range(8):
                x=sx+dx
                if x>=WIDTH or (x<8 and not spr_left):continue
                source_x=7-dx if attributes&0x40 else dx
                value=sprite_pixel(ppu,tile,source_x,source_y,height,sprite_base)
                if value==0:continue
                idx=y*WIDTH+x
                if attributes&0x20 and opaque[idx]:continue
                pixels[idx]=palette_color(ppu,0x10+4*(attributes&3)+value)
    return bytes(pixels)

def compare_pixels(predicted,observed):
    if len(predicted)!=PIXELS or len(observed)!=PIXELS:
        raise ValueError('Reference and predicted frames must contain 61440 pixels')
    checked=bad=unknown=0
    rows=[]
    heat=bytearray(PIXELS*3)
    for y in range(HEIGHT):
        row_bad=row_checked=0
        for x in range(WIDTH):
            i=y*WIDTH+x
            actual=observed[i]
            if actual==254:
                unknown+=1
                rgb=(60,99,150)
            elif actual==predicted[i]:
                checked+=1
                row_checked+=1
                rgb=(42,57,62)
            else:
                checked+=1
                row_checked+=1
                row_bad+=1
                bad+=1
                rgb=(239,73,58)
            heat[3*i:3*i+3]=bytes(rgb)
        rows.append({'row':y,'different':row_bad,'compared':row_checked})
    return {'compared_pixels':checked,'different_pixels':bad,
            'matching_pixels':checked-bad,'unknown_palette_pixels':unknown,
            'mismatch_fraction':round(bad/checked,6) if checked else None,
            'highest_mismatch_scanlines':sorted(rows,key=lambda row:(-row['different'],row['row']))[:12]
           },Image.frombytes('RGB',(WIDTH,HEIGHT),bytes(heat))

def meta_byte(metadata,key):
    val=metadata.get(key,'unknown')
    if val=='unknown':return None
    try: n=int(val,16)
    except ValueError:raise ValueError('Invalid '+key) from None
    if not 0<=n<=255:raise ValueError('Invalid '+key)
    return n

def evaluate(prefix,nt=0,base=None,mode='background',scroll_x=0,scroll_y=0):
    snap=load_snapshot(prefix)
    if hasattr(snap,'ppu'):
        ppu,ram,meta=snap.ppu,snap.ram,snap.metadata
    else:
        ppu,ram,meta=snap
    rgb,reference=load_reference(prefix)
    ctrl=meta_byte(meta,'ppuctrl')
    if base is None:
        if ctrl is None:
            raise ValueError('PPUCTRL unknown; set --pattern-base')
        base=0x1000 if ctrl&0x10 else 0
    if mode not in ('background','sprites'):
        raise ValueError('Invalid comparison mode')
    if mode=='sprites' and ctrl is None:
        raise ValueError('Cannot determine sprite height/table without PPUCTRL')
    mask=meta_byte(meta,'ppumask')
    proposed=reconstructed_indices(ppu,ram,nt,base,
        sprites=mode=='sprites',
        height=16 if ctrl is not None and ctrl&0x20 else 8,
        sprite_base=0x1000 if ctrl is not None and ctrl&0x08 else 0,
        mask=mask,scroll_x=scroll_x,scroll_y=scroll_y)
    result,heatmap=compare_pixels(proposed,reference)
    result.update({
        'frame':meta.get('frame'),'input_prefix':str(prefix),
        'mode':mode,'nametable':nt,'bg_pattern_base':hex(base),
        'scroll_x':scroll_x,'scroll_y':scroll_y,
        'ppuctrl_observed':ctrl is not None,'ppumask_observed':mask is not None,
        'rgb_capture_bytes':len(rgb),
        'limitations':'Scroll offsets are assumptions unless independently measured. '
          'Discrepancies may be due to scroll splits, midframe CHR swaps, '
          'sprites, emphasis, PPU timing and static snapshot limitations; '
          'a low error fraction does NOT establish authentic game reconstruction.'
    })
    return result,heatmap

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('capture_prefix',type=Path)
    ap.add_argument('--nametable',type=int,choices=[0,1,2,3],default=0)
    ap.add_argument('--pattern-base',choices=['auto','0x0000','0x1000'],default='auto')
    ap.add_argument('--mode',choices=['background','sprites'],default='background')
    ap.add_argument('--scroll-x',type=int,default=None,
                    help='Measured X scroll (0..255); omit for assumed zero')
    ap.add_argument('--scroll-y',type=int,default=None,
                    help='Measured Y scroll (0..239); omit for assumed zero')
    ap.add_argument('--out',type=Path,default=Path('private/reference_comparison'))
    args=ap.parse_args()
    base=None if args.pattern_base=='auto' else int(args.pattern_base,16)
    result,heatmap=evaluate(args.capture_prefix,args.nametable,base,args.mode,
        0 if args.scroll_x is None else args.scroll_x,
        0 if args.scroll_y is None else args.scroll_y)
    result['scroll_provenance']=('explicit' if args.scroll_x is not None
        and args.scroll_y is not None else 'partially_or_fully_assumed_zero')
    args.out.mkdir(parents=True,exist_ok=True)
    report=args.out/(args.capture_prefix.name+'_comparison.json')
    difference=args.out/(args.capture_prefix.name+'_difference.png')
    observed=args.out/(args.capture_prefix.name+'_observed.png')
    report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    heatmap.save(difference)
    rgb,_=load_reference(args.capture_prefix)
    Image.frombytes('RGB',(WIDTH,HEIGHT),rgb).save(observed)
    print(json.dumps({'report':str(report),'difference':str(difference),
        'observed':str(observed),'mismatch_fraction':result['mismatch_fraction'],
        'private_data_warning':'Never commit original NES frames or memory snapshots'},indent=2))

if __name__=='__main__':main()
