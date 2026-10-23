#!/usr/bin/env python3
"""ROM-free implementation; owner-local authenticated FCEUX RGB background-motion audit.

Never ship original RGB, palette planes, ROM, FM2, trace rows or private digests
in public GitHub. Pixel shift in selected non-sprite bands is not NES PPU dot
or global camera/road-physics evidence.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

WIDTH, HEIGHT = 256, 240
GD_HEADER = bytes((255,254,1,0,0,240,1,255,255,255,255))
FIRST, LAST = 420, 444
# Verified from private native 256x240 frame inspection; none overlaps car or HUD.
# Deliberately treat these as candidate background/road-marking TEXTURE windows,
# not automatic proof of road edges, perspective or collision lanes.
BANDS = {
    'left_environment': (0, 52, 20, 175),
    'right_environment': (195, 255, 20, 175),
    'left_marking': (93, 99, 20, 175),
    'right_marking': (157, 163, 20, 175),
}
SHIFTS=tuple(range(-4,5))
POINTS=((0,0),(127,32),(128,120),(64,180),(192,200),(255,239))


def digest(p:Path)->str:
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()


def checked(p:Path,sha:str,*,min_size:int=1,max_size:int=80_000_000)->None:
    if p.is_symlink() or not p.is_file() or not min_size<=p.stat().st_size<=max_size:
        raise ValueError('missing, linked, oversized or empty original private source')
    if not isinstance(sha,str) or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):
        raise ValueError('invalid private expected digest')
    if digest(p)!=sha: raise ValueError('private source SHA-256 mismatch')


def read_frame(p:Path,sha:str)->bytes:
    checked(p,sha,min_size=11+WIDTH*HEIGHT*4,max_size=11+WIDTH*HEIGHT*4)
    raw=p.read_bytes()
    if raw[:11]!=GD_HEADER or any(raw[i] for i in range(11,len(raw),4)):
        raise ValueError('original FCEUX GD pixel format differs')
    rgb=bytearray(WIDTH*HEIGHT*3)
    rgb[0::3]=raw[12::4];rgb[1::3]=raw[13::4];rgb[2::3]=raw[14::4]
    return bytes(rgb)


def mismatch_fraction(a:bytes,b:bytes,band:tuple[int,int,int,int],dy:int)->float:
    x0,x1,y0,y1=band
    if not -4<=dy<=4 or not 0<=x0<x1<=WIDTH or not 0<=y0<y1<=HEIGHT:
        raise ValueError('invalid fixed masked texture window/shift')
    start=max(y0,y0-dy);end=min(y1,y1-dy)
    if end<=start:raise ValueError('no region overlap')
    changed=0
    for y in range(start,end):
        ai=(y*WIDTH+x0)*3;bi=((y+dy)*WIDTH+x0)*3
        # pixels, rather than byte counts: a change in any RGB channel counts once.
        for col in range(x1-x0):
            i=ai+3*col;j=bi+3*col
            changed += a[i:i+3]!=b[j:j+3]
    return changed/((end-start)*(x1-x0))


def score_band(a:bytes,b:bytes,band:tuple[int,int,int,int],*,name:str)->tuple[int,float,float]:
    rank=sorted((mismatch_fraction(a,b,band,dy),dy) for dy in SHIFTS)
    best,runner=rank[:2]
    # Background texture must discriminate alternatives; an all-grey flat lane is
    # NOT evidence of zero motion. Strip bands have fewer feature-bearing pixels.
    min_gap=0.008 if 'marking' in name else 0.045
    if runner[0]-best[0]<min_gap:
        raise ValueError('texture-shift score ambiguous/flat (fail closed)')
    max_err=0.17 if 'marking' in name else 0.16
    if best[0]>max_err:
        raise ValueError('candidate background scene change or untrusted motion score')
    return best[1],best[0],runner[0]-best[0]


def verify_frame_anchors(path:Path,field:str,event:str,first:int,last:int)->None:
    seen=Counter()
    with path.open('r',newline='',encoding='utf-8-sig') as inp:
        rows=csv.DictReader(inp,delimiter='\t')
        if not rows.fieldnames or field not in rows.fieldnames or 'event' not in rows.fieldnames:
            raise ValueError('original CPU/PPU frame witness header differs')
        for row in rows:
            if row['event']==event:seen[int(row[field])]+=1
    if len(seen)!=261 or any(seen[f]!=1 for f in range(380,641)):
        raise ValueError('original same-session CPU/PPU frame coverage incomplete')


def audit(root:Path,manifest:Path,*,first:int=FIRST,last:int=LAST)->dict:
    if first>last or last-first>32 or not 380<=first<=last<=640:
        raise ValueError('unsupported original source frame interval')
    if root.is_symlink() or manifest.is_symlink() or not root.is_dir() or not manifest.is_file():
        raise ValueError('private witness/manifest unavailable or linked')
    m=json.loads(manifest.read_text(encoding='utf8'))
    if m.get('format')!='vpd_stage344_original_consecutive_rgb_private_manifest_v1':
        raise ValueError('unrecognized private authentication manifest')
    if m.get('original_readonly') is not True or m.get('newppu')!=0 or m.get('frames')!=list(range(first,last+1)):
        raise ValueError('original FM2 playback mode/source frame selection differs')
    expected=m.get('sha256',{})
    cpu=root/'stage335_ppu_latch_ram0d_events.tsv'
    native=root/'stage341_classic_refreshaddr.tsv'
    checked(cpu,expected['stage335_ppu_latch_ram0d_events.tsv'])
    checked(native,expected['stage341_classic_refreshaddr.tsv'])
    if expected['stage335_ppu_latch_ram0d_events.tsv']!=m.get('sealed_cpu_sha256') or expected['stage341_classic_refreshaddr.tsv']!=m.get('sealed_native_sha256'):
        raise ValueError('same-session original source identity differs from sealed previous stages')
    verify_frame_anchors(cpu,'frame','frame_begin',380,640)
    verify_frame_anchors(native,'core_frame_ordinal','core_frame_start',380,640)
    marker=root/'COMPLETE.txt'
    checked(marker,expected['COMPLETE.txt'],min_size=30,max_size=10000)
    text=marker.read_text()
    if not all(s in text.splitlines() for s in ('rom_identity_verified=yes','fm2_readonly=yes','frames=261','first_frame=380','last_frame=640')):
        raise ValueError('original movie completion marker invalid')
    frames={}
    for frame in range(first,last+1):
        name=f'stage343_rgb_{frame:04d}.gd'
        frames[frame]=read_frame(root/name,expected[name])
    if len(list(root.glob('stage343_rgb_*.gd')))!=last-first+1:
        raise ValueError('unexpected/missing unselected original RGB frame')
    # Stage343 source Lua wrote palette samples under the same frame callback.
    probes=root/'stage343_rgb_palette_probes.tsv'
    checked(probes,expected[probes.name],min_size=100,max_size=20000)
    nprobes=0
    probed_indices={}
    with probes.open('r',newline='') as inp:
        reader=csv.DictReader(inp,delimiter='\t')
        if reader.fieldnames!=['frame','x','y','r','g','b','palette_index']:
            raise ValueError('source RGB probe schema mismatch')
        coverage=Counter()
        for row in reader:
            frame=int(row['frame']);x=int(row['x']);y=int(row['y'])
            if frame not in frames or (x,y) not in POINTS or not all(0<=int(row[q])<=255 for q in ('r','g','b','palette_index')):
                raise ValueError('invalid/outside original RGB palette sample')
            i=(y*WIDTH+x)*3
            if frames[frame][i:i+3]!=bytes(int(row[k]) for k in ('r','g','b')):
                raise ValueError('source frame RGB does not match independently sampled RGB')
            coverage[frame]+=1;nprobes+=1
            key=(frame,x,y)
            if key in probed_indices:raise ValueError('duplicate original RGB palette probe')
            probed_indices[key]=int(row['palette_index'])
        if any(coverage[f]!=len(POINTS) for f in frames):
            raise ValueError('original frame palette probe coverage mismatch')
    palette_frames=m.get('palette_frames')
    if palette_frames!=[first,(first+last)//2,last]:
        raise ValueError('expected three full indexed palette frames missing')
    for f in palette_frames:
        n=f'stage343_palette_{f:04}.idx';p=root/n
        checked(p,expected[n],min_size=WIDTH*HEIGHT,max_size=WIDTH*HEIGHT)
        contents=p.read_bytes()
        if any(contents[y*WIDTH+x]!=probed_indices[(f,x,y)] for x,y in POINTS):
            raise ValueError('indexed source palette probe differs')
    shifts=Counter();residuals=[];pair_count=0
    for f in range(first,last):
        candidate={name:score_band(frames[f],frames[f+1],band,name=name) for name,band in BANDS.items()}
        disp={v[0] for v in candidate.values()}
        if len(disp)!=1:raise ValueError('masked background bands disagree on motion')
        d=disp.pop();shifts[d]+=1;pair_count+=1
        residuals.extend(v[1] for v in candidate.values())
    if pair_count!=last-first or sum(shifts.values())!=pair_count:
        raise ValueError('missing adjacent frame pair')
    return {
        'format':'vpd_stage344_private_visual_displacement_aggregate_v1',
        'source_window_frames':261,
        'consecutive_original_rgb_frames':last-first+1,
        'adjacent_frame_pairs_verified':pair_count,
        'native_resolution':[WIDTH,HEIGHT],
        'full_indexed_palette_frames_verified':len(palette_frames),
        'independent_rgb_sample_matches':nprobes,
        'background_texture_bands_consensus_per_pair':True,
        'masked_background_vertical_shift_pixel_counts':{str(k):shifts[k] for k in sorted(shifts)},
        'max_best_shift_mismatch_fraction':round(max(residuals),4),
        'original_cpu_and_ppu_byte_identical_to_sealed_sources':True,
        'sprite_hud_excluded_from_displacement_windows':True,
        'actual_hardware_ppu_dot_proven':False,
        'road_geometry_or_sprite_collision_proven':False,
        'general_camera_speed_proven':False,
        'full_screen_motion_proven':False,
        'private_original_pixels_disclosed':False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:
        result=audit(a.root,a.manifest)
        payload=json.dumps(result,indent=2,sort_keys=True)+'\n'
        if a.output:
            if a.output.exists() or a.output.is_symlink():raise ValueError('do not overwrite owner-private report')
            a.output.write_text(payload)
        else: print(payload,end='')
    except (OSError,ValueError,KeyError,TypeError,UnicodeError,json.JSONDecodeError):
        p.exit(1,'VPD_STAGE344_ORIGINAL_MOTION_INCONCLUSIVE\n')
if __name__=='__main__':main()
