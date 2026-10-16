#!/usr/bin/env python3
"""Build a strict, ROM-private 8px tile mosaic from observed FCEUX PPU frames.

This is NOT a level-format or collision-map decoder. It relates observed
nametable bytes to independently measured camera and scroll coordinates.
Raster splits, MMC3 midframe CHR changes and screen-effective tiles remain
unproven by any single postframe PPU snapshot. No original assets in Git.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

WIDTH,HEIGHT=256,240

def _integer(obj,key,lo,hi):
    v=obj.get(key)
    if type(v) is not int or not lo<=v<=hi:
        raise ValueError(f'{key}: expected integer {lo}..{hi}')
    return v

def _rom_md5(value):
    if not isinstance(value,str) or len(value)!=32 or any(
        c not in '0123456789abcdefABCDEF' for c in value):
        raise ValueError('rom_md5 must be 32 hexadecimal characters')
    return value.lower()

def _metadata(path):
    result={}
    for line in path.read_text(encoding='utf8').splitlines():
        if not line or line.startswith('#'):continue
        if '=' not in line:raise ValueError('Malformed metadata')
        key,value=line.split('=',1)
        if key in result:raise ValueError('Duplicate metadata key '+key)
        result[key]=value
    return result

def validate_manifest(data):
    if not isinstance(data,dict) or set(data)!={'schema','rom_md5','captures'}:
        raise ValueError('Expected schema, rom_md5 and captures')
    if type(data['schema']) is not int or data['schema']!=1:
        raise ValueError('Unsupported manifest version')
    _rom_md5(data['rom_md5'])
    captures=data['captures']
    if not isinstance(captures,list) or not 1<=len(captures)<=128:
        raise ValueError('Expected 1..128 capture records')
    fields={'prefix','frame','camera_x','camera_y','scroll_x','scroll_y',
            'nametable','screen_y_start','screen_y_end',
            'camera_source','scroll_source'}
    for c in captures:
        if not isinstance(c,dict) or set(c)!=fields:
            raise ValueError('Each capture requires explicit measurement provenance')
        if not isinstance(c['prefix'],str) or not c['prefix'] or '\x00' in c['prefix']:
            raise ValueError('Invalid capture prefix')
        _integer(c,'frame',0,10**9)
        _integer(c,'camera_x',-32768,32767)
        _integer(c,'camera_y',-32768,32767)
        _integer(c,'scroll_x',0,255)
        _integer(c,'scroll_y',0,239)
        _integer(c,'nametable',0,3)
        lo=_integer(c,'screen_y_start',0,239)
        hi=_integer(c,'screen_y_end',1,240)
        if lo>=hi:raise ValueError('Empty screen scanline interval')
        for key in ('camera_source','scroll_source'):
            if not isinstance(c[key],str) or len(c[key].strip())<8:
                raise ValueError('Supply a documented '+key)
        if ((c['camera_x']-c['scroll_x'])%8 or
            (c['camera_y']-c['scroll_y'])%8):
            raise ValueError('World-camera and PPU-scroll tile phases disagree')
    return data

def sampled_tile(ppu,base_nt,sx,sy,scroll_x,scroll_y):
    """Return (tile ID, 2-bit attribute palette, logical nametable)."""
    if len(ppu)!=0x4000:raise ValueError('Expected 16KiB PPU snapshot')
    if base_nt not in range(4) or not 0<=sx<256 or not 0<=sy<240:
        raise ValueError('Nametable/sample outside range')
    if not 0<=scroll_x<=255 or not 0<=scroll_y<=239:
        raise ValueError('Unsupported PPU scrolling offset')
    ax=sx+scroll_x
    ay=sy+scroll_y
    nt=base_nt^((ax//256)&1)^(((ay//240)&1)<<1)
    tx=(ax%256)//8
    ty=(ay%240)//8
    b=0x2000+nt*1024
    tile=ppu[b+ty*32+tx]
    attr=ppu[b+960+(ty//4)*8+tx//4]
    quadrant=((ty%4)//2)*2+((tx%4)//2)
    return tile,(attr>>(2*quadrant))&3,nt

def _tile_centers(camera,start,end):
    first=start+(4-(camera+start))%8
    for sx in range(first,end,8):
        yield sx,(camera+sx)//8

def reconstruct(data,manifest_path,allow_incomplete=False):
    validate_manifest(data)
    root=Path(manifest_path).parent
    expected_md5=_rom_md5(data['rom_md5'])
    observations=defaultdict(lambda:defaultdict(list))
    frames=[]
    for entry in data['captures']:
        prefix=Path(entry['prefix'])
        if not prefix.is_absolute():prefix=root/prefix
        meta=_metadata(Path(str(prefix)+'.meta.txt'))
        if _rom_md5(meta.get('rom_md5'))!=expected_md5:
            raise ValueError('ROM MD5 mismatch: '+str(prefix))
        if meta.get('frame')!=str(entry['frame']):
            raise ValueError('Frame number mismatch: '+str(prefix))
        complete=(meta.get('register_log_complete')=='yes' and
                  meta.get('dropped_register_writes')=='0')
        if not complete and not allow_incomplete:
            raise ValueError('Incomplete or unverified register log: '+str(prefix))
        if meta.get('format') not in (
            'fceux_ppu_snapshot_v3','fceux_ppu_snapshot_v4'):
            raise ValueError('Unsupported capture metadata format')
        ppu=Path(str(prefix)+'.ppu.bin').read_bytes()
        if len(ppu)!=16384:raise ValueError('Expected 16384 PPU bytes')
        n=0
        for sx,wx in _tile_centers(entry['camera_x'],0,256):
            for sy,wy in _tile_centers(entry['camera_y'],
                                      entry['screen_y_start'],entry['screen_y_end']):
                tile,pal,nt=sampled_tile(
                    ppu,entry['nametable'],sx,sy,entry['scroll_x'],entry['scroll_y'])
                observations[(wx,wy)][(tile,pal)].append({
                    'frame':entry['frame'],'prefix':str(prefix),'nametable':nt})
                n+=1
        frames.append({
            'frame':entry['frame'],'samples':n,
            'world_camera':[entry['camera_x'],entry['camera_y']],
            'screen_y_interval':[entry['screen_y_start'],entry['screen_y_end']],
            'ppu_sha256':hashlib.sha256(ppu).hexdigest(),'log_complete':complete,
            'camera_source':entry['camera_source'],
            'scroll_source':entry['scroll_source']})
    tiles=[]
    conflicts=overlaps=0
    for (wx,wy),candidates in sorted(
            observations.items(),key=lambda v:(v[0][1],v[0][0])):
        total=sum(len(v) for v in candidates.values())
        if total>1:overlaps+=1
        conflict=len(candidates)>1
        if conflict:conflicts+=1
        agreed=next(iter(candidates)) if not conflict else None
        tiles.append({
            'world_tile_x':wx,'world_tile_y':wy,
            'agreed_tile_id':agreed[0] if agreed else None,
            'agreed_attribute_palette':agreed[1] if agreed else None,
            'observations':total,'conflict':conflict,
            'candidates':[{'tile_id':tile,'palette':pal,'count':len(src),
                           'sources':src} for (tile,pal),src in sorted(candidates.items())]})
    return {
        'schema':1,
        'classification':'observed PPU nametable tile hypothesis; NOT collision geometry',
        'rom_md5':expected_md5,'capture_count':len(frames),
        'captures':frames,'sampled_world_tiles':len(tiles),
        'repeated_world_tiles':overlaps,'conflicting_world_tiles':conflicts,
        'tile_observations':tiles,
        'limitations':[
            'Postframe PPU memory is not the scanline-effective image under MMC3 splits',
            'Camera and scroll are independent external measurements, never guessed here',
            'Tile IDs and attribute bits do not identify collisions, NPCs or stage events',
            'All live capture outputs and derived original-game mosaics must stay private'
        ]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path)
    p.add_argument('--out',type=Path,
                   default=Path('private/stage_tile_observations.json'))
    p.add_argument('--allow-incomplete',action='store_true',
                   help='Accept incomplete captures but mark them as such')
    args=p.parse_args()
    data=json.loads(args.manifest.read_text(encoding='utf8'))
    result=reconstruct(data,args.manifest,args.allow_incomplete)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({
        'captured_frames':result['capture_count'],
        'world_tile_cells':result['sampled_world_tiles'],
        'conflicting_cells':result['conflicting_world_tiles'],
        'private_report':str(args.out),
        'warning':'Evidence-gated PPU observations only, not recovered collisions'
    },indent=2))

if __name__=='__main__':main()
