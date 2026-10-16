#!/usr/bin/env python3
"""End-to-end verification with the original ROM supplied by its owner."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tools'))
from inspect_rom import parse_rom
from disassemble_fixed_bank import decode

p=argparse.ArgumentParser();p.add_argument('rom');p.add_argument('--cli',help='Path to compiled vpd_chr_cli')
a=p.parse_args()
rom=parse_rom(a.rom)
assert rom['mapper']==4 and len(rom['prg'])==131072 and len(rom['chr'])==131072
assert len(rom['data'])==262160
assert hashlib.sha256(rom['data']).hexdigest()=="4ce488710acc6ba9aba812c69ab7a7c2a08587f9fef95ec6e5a67b50792e2cf2", 'ROM differs from the audited USA revision'
prg=rom['prg']
vectors={name:int.from_bytes(prg[-pos:-pos+2 if pos!=2 else None],'little') for name,pos in [('NMI',6),('RESET',4),('IRQ',2)]}
assert vectors=={'NMI':0xE5A2,'RESET':0xE39E,'IRQ':0xE1DA}
fixed=prg[-8192:]
assert decode(fixed,0xE39E)['asm']=='SEI'
assert decode(fixed,0xE1DF)['asm']=='STA $E000'
assert decode(fixed,0xE5AE)['asm']=='STA $4014'
for n in range(32):
    image=Image.open(root/'atlases'/f'chr_page_{n:02d}.png')
    assert image.size==(256,256)
    bmp=root/'switch_viewer'/'assets'/f'chr_page_{n:02d}.bmp'
    if bmp.exists():
        assert Image.open(bmp).convert('RGB').tobytes()==image.convert('RGB').tobytes(),n
obj=json.loads((root/'reports'/'static_rom_analysis.json').read_text())
assert obj['chr_tile_count']==8192 and obj['unique_chr_tiles']==7194
assert obj['chr_page_count']==32
print('PASS: authentic ROM SHA-256, vectors, 6502 instruction samples, all 32 atlases, manifest')
