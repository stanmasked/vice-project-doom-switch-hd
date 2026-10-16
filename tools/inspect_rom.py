#!/usr/bin/env python3
"""NES 2.0 / iNES static CHR + PRG analyzer, ROM never modified."""
from pathlib import Path
import argparse
import collections
import hashlib
import json
from PIL import Image, ImageDraw

INKS = [(18,22,33),(86,108,136),(172,195,214),(248,249,250)]


def parse_rom(path):
    data=Path(path).read_bytes()
    if len(data)<16 or data[:4]!=b'NES\x1a':
        raise ValueError('Missing NES header')
    h=data[:16]
    nes2 = (h[7]&0x0c)==0x08
    mapper=(h[6]>>4)|(h[7]&0xf0)| (((h[8]&0x0f)<<8) if nes2 else 0)
    if nes2:
        def size(base, high, unit):
            if high == 0x0f:
                return (2**(base>>2))*(2*(base&3)+1)
            return ((high<<8)|base)*unit
        prg_len=size(h[4],h[9]&15,16384)
        chr_len=size(h[5],h[9]>>4,8192)
    else:
        prg_len=h[4]*16384
        chr_len=h[5]*8192
    start=16+(512 if h[6]&4 else 0)
    if len(data)<start+prg_len+chr_len:
        raise ValueError('Truncated ROM')
    return {'data':data,'header':h,'nes2':nes2,'mapper':mapper,'prg':data[start:start+prg_len],
        'chr':data[start+prg_len:start+prg_len+chr_len], 'trailing':len(data)-start-prg_len-chr_len,
        'sha256':hashlib.sha256(data).hexdigest(),'file':Path(path).name}


def tile_indices(tile):
    assert len(tile)==16
    out=[]
    for y in range(8):
        for x in range(8):
            mask=128>>x
            out.append(int(bool(tile[y]&mask))+(int(bool(tile[8+y]&mask))<<1))
    return out


def render_page(tiles, size=2):
    w=16*8*size
    im=Image.new('RGB',(w,w))
    px=im.load()
    for n,tile in enumerate(tiles):
        dx=n%16*8*size; dy=n//16*8*size
        for i,v in enumerate(tile_indices(tile)):
            x=dx+(i%8)*size; y=dy+(i//8)*size
            for iy in range(size):
                for ix in range(size):px[x+ix,y+iy]=INKS[v]
    return im


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('rom',help='Path to user-owned NES ROM')
    ap.add_argument('--out',default='.',help='Output directory')
    args=ap.parse_args()
    rom=parse_rom(args.rom)
    out=Path(args.out); (out/'atlases').mkdir(parents=True,exist_ok=True); (out/'reports').mkdir(parents=True,exist_ok=True)
    prg,chr=rom['prg'],rom['chr']
    if len(chr)%16:raise ValueError('CHR size not tile-aligned')
    tiles=[chr[i:i+16] for i in range(0,len(chr),16)]
    unique=len(set(tiles))
    counts=collections.Counter(tiles)
    duplicate_tile_count=sum(v-1 for v in counts.values())
    blank=bytes(16)
    empty=sum(t==blank for t in tiles)
    all_zero_banks=[]
    chr_banks=[]
    for i in range(len(chr)//1024):
        bank=chr[i*1024:(i+1)*1024]
        chr_banks.append({'index':i,'size':len(bank),'sha256':hashlib.sha256(bank).hexdigest(),
            'unique_tiles':len(set(bank[j:j+16] for j in range(0,1024,16))),
            'blank_tiles':sum(bank[j:j+16]==blank for j in range(0,1024,16))})
        if not any(bank):all_zero_banks.append(i)
    prg_banks=[{'index':i,'size':8192,'sha256':hashlib.sha256(prg[i*8192:(i+1)*8192]).hexdigest()} for i in range(len(prg)//8192)]
    atlas_count=(len(tiles)+255)//256
    preview=Image.new('RGB',(4*256,8*282),(242,243,246))
    draw=ImageDraw.Draw(preview)
    for i in range(atlas_count):
        page=render_page(tiles[i*256:(i+1)*256],size=2)
        page.save(out/'atlases'/f'chr_page_{i:02d}.png')
        if i<32:
            x=(i%4)*256; y=(i//4)*282
            preview.paste(page,(x,y+23))
            draw.text((x+6,y+4),f'CHR page {i:02d} | tiles {i*256:04d}-{min(len(tiles)-1,(i+1)*256-1):04d}', fill=(29,36,45))
    preview.save(out/'chr_all_pages_overview.png')
    vectors={name:int.from_bytes(prg[-off:-off+2 if off!=2 else None],'little') for name,off in [('NMI',6),('RESET',4),('IRQ',2)]}
    obj={'file':rom['file'],'bytes':len(rom['data']),'sha256':rom['sha256'],'header':rom['header'].hex(),
        'format':'NES 2.0' if rom['nes2'] else 'iNES','mapper':rom['mapper'],
        'submapper':rom['header'][8]>>4 if rom['nes2'] else None,
        'prg_bytes':len(prg),'chr_bytes':len(chr),'trailing_bytes':rom['trailing'],
        'prg_8k_banks':prg_banks,'chr_1k_banks':chr_banks,
        'chr_page_count':atlas_count,'chr_tile_count':len(tiles),'unique_chr_tiles':unique,
        'repeated_tiles_across_chr':duplicate_tile_count,'fully_zero_tiles':empty,
        'fully_zero_chr_1k_banks':all_zero_banks,
        'vector_candidates':{k:f'0x{v:04X}' for k,v in vectors.items()},
        'vector_candidates_mapping':'Assumes last 8 KiB PRG is fixed at CPU $E000-$FFFF in MMC3 mode'}
    (out/'reports'/'static_rom_analysis.json').write_text(json.dumps(obj,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in obj.items() if k not in ('chr_1k_banks','prg_8k_banks')},indent=2))

if __name__=='__main__':main()
