#!/usr/bin/env python3
"""Static NES background reconstruction from an FCEUX PPU memory capture.
Research only: no scanline IRQ, scrolling, sprite compositing or NES emulation.
Keep all screenshots / captures outside GitHub.
"""
import argparse, hashlib, json
from pathlib import Path
from PIL import Image

NES_RGB=[
(84,84,84),(0,30,116),(8,16,144),(48,0,136),(68,0,100),(92,0,48),(84,4,0),(60,24,0),(32,42,0),(8,58,0),(0,64,0),(0,60,0),(0,50,60),(0,0,0),(0,0,0),(0,0,0),
(152,150,152),(8,76,196),(48,50,236),(92,30,228),(136,20,176),(160,20,100),(152,34,32),(120,60,0),(84,90,0),(40,114,0),(8,124,0),(0,118,40),(0,102,120),(0,0,0),(0,0,0),(0,0,0),
(236,238,236),(76,154,236),(120,124,236),(176,98,236),(228,84,236),(236,88,180),(236,106,100),(212,136,32),(160,170,0),(116,196,0),(76,208,32),(56,204,108),(56,180,204),(60,60,60),(0,0,0),(0,0,0),
(236,238,236),(168,204,236),(188,188,236),(212,178,236),(236,174,236),(236,174,212),(236,180,176),(228,196,144),(204,210,120),(180,222,120),(168,226,144),(152,226,180),(160,214,228),(160,162,160),(0,0,0),(0,0,0)]

def load_snapshot(prefix):
    prefix=Path(prefix)
    ppu=Path(str(prefix)+'.ppu.bin').read_bytes()
    if len(ppu)!=0x4000: raise ValueError('PPU memory capture must be 16384 bytes')
    ram_path=Path(str(prefix)+'.ram.bin')
    ram=ram_path.read_bytes() if ram_path.exists() else None
    if ram is not None and len(ram)!=0x800: raise ValueError('CPU RAM capture must be 2048 bytes')
    meta={}
    meta_path=Path(str(prefix)+'.meta.txt')
    if meta_path.exists():
        for line in meta_path.read_text(encoding='utf-8').splitlines():
            if not line or line.startswith('#'):continue
            if '=' not in line:raise ValueError('Malformed metadata line')
            key,val=line.split('=',1)
            if key in meta:raise ValueError('Duplicate metadata key '+key)
            meta[key]=val
    return ppu,ram,meta

def palette_color(ppu,entry):
    if not 0<=entry<32:raise ValueError('Palette entry outside 0..31')
    if entry in (0x10,0x14,0x18,0x1c):entry-=16
    return ppu[0x3f00+entry]&63

def bg_pixel(ppu,nametable,x,y,pattern_base):
    if len(ppu)!=0x4000:raise ValueError('Expected 16KiB PPU memory')
    if not 0<=nametable<4:raise ValueError('Nametable outside 0..3')
    if not 0<=x<256 or not 0<=y<240:raise ValueError('Pixel outside screen')
    if pattern_base not in (0,0x1000):raise ValueError('Pattern base outside 0/0x1000')
    tx,ty=x//8,y//8
    base=0x2000+nametable*0x400
    tile=ppu[base+ty*32+tx]
    attr=ppu[base+960+(ty//4)*8+(tx//4)]
    quadrant=((ty%4)//2)*2+((tx%4)//2)
    palette=(attr>>(2*quadrant))&3
    offset=pattern_base+tile*16+y%8
    shift=7-x%8
    pixel=((ppu[offset]>>shift)&1)|(((ppu[offset+8]>>shift)&1)<<1)
    entry=0 if pixel==0 else 4*palette+pixel
    return palette_color(ppu,entry)

def render_background(ppu,nametable=0,pattern_base=0,scale=2):
    if not 1<=scale<=8:raise ValueError('Scale must be 1..8')
    out=Image.new('RGB',(256,240))
    pixels=out.load()
    for y in range(240):
        for x in range(256):pixels[x,y]=NES_RGB[bg_pixel(ppu,nametable,x,y,pattern_base)]
    return out.resize((256*scale,240*scale),Image.Resampling.NEAREST) if scale!=1 else out

def pattern_bases(meta,requested='auto'):
    if requested!='auto':return [int(requested,0)],'manual'
    try:
        ctrl=int(meta.get('ppuctrl','unknown'),16)
        if not 0<=ctrl<=255:raise ValueError('bad')
        return [0x1000 if ctrl&0x10 else 0],'observed PPUCTRL'
    except ValueError:return [0,0x1000],'unknown PPUCTRL; both alternatives rendered'

def inspect(ppu,ram,meta,pattern_selection):
    nts=[]
    for n in range(4):
        raw=ppu[0x2000+n*1024:0x2000+(n+1)*1024]
        nts.append({'id':n,'nonzero_tile_cells':sum(x!=0 for x in raw[:960]),
                    'unique_tile_ids':len(set(raw[:960]))})
    out={'frame':meta.get('frame'),'ppu_sha256':hashlib.sha256(ppu).hexdigest(),
         'palette_index_entries':[palette_color(ppu,i) for i in range(32)],
         'nametables':nts,'pattern_candidates':pattern_selection,'metadata':meta,
         'limitations':['Static mapped PPU memory, not a whole-frame image',
                        'IRQ bank switching, sprites, scrolling and video filtering not reproduced']}
    if ram is not None:
        out['chr_zero_page_3d_42']=list(ram[0x3d:0x43])
        out['queue_head_0600_060f']=list(ram[0x600:0x610])
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture_prefix',type=Path)
    p.add_argument('--out',type=Path,default=Path('private/preview'))
    p.add_argument('--nametable',choices=['all','0','1','2','3'],default='all')
    p.add_argument('--pattern-base',choices=['auto','0x0000','0x1000'],default='auto')
    p.add_argument('--scale',type=int,default=2)
    a=p.parse_args()
    ppu,ram,meta=load_snapshot(a.capture_prefix)
    bases,reason=pattern_bases(meta,a.pattern_base)
    nts=list(range(4)) if a.nametable=='all' else [int(a.nametable)]
    a.out.mkdir(parents=True,exist_ok=True)
    images=[]
    for base in bases:
        for n in nts:
            output=a.out/f'{a.capture_prefix.name}_nt{n}_pattern{base:04X}.png'
            render_background(ppu,n,base,a.scale).save(output)
            images.append(str(output))
    report=inspect(ppu,ram,meta,bases)
    report['pattern_selection_reason']=reason
    report['rendered_files']=images
    report_path=a.out/(a.capture_prefix.name+'_analysis.json')
    report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'report':str(report_path),'images':images,'PRIVATE':'Do not commit images or captures'},indent=2))

if __name__=='__main__':main()
