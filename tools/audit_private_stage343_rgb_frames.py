#!/usr/bin/env python3
"""Validate private same-session original NES 256x240 RGB/GD and PPU witnesses.

No original screenshot, palette, input value, or source digest appears in output.
Renderer XBuf at emu.registerafter is an emulator image, not a hardware PPU dot.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

W,H=256,240
HEADER=bytes((255,254,1,0,0,240,1,255,255,255,255))
POINTS=((0,0),(127,32),(128,120),(64,180),(192,200),(255,239))
LIMIT=50_000_000


def checksum(p:Path)->str:
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def checked(p:Path,expected:str,lo=1,hi=LIMIT)->None:
    if p.is_symlink() or not p.is_file() or not lo<=p.stat().st_size<=hi:
        raise ValueError('missing/linked/incorrectly sized owner-private witness')
    if (len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected)
            or checksum(p)!=expected):raise ValueError('private source SHA-256 mismatch')


def parse_gd(data:bytes)->bytes:
    if len(data)!=11+W*H*4 or data[:11]!=HEADER:
        raise ValueError('native 256x240 FCEUX XBuf GD header/size mismatch')
    pix=data[11:]
    if any(pix[j] for j in range(0,len(pix),4)):
        raise ValueError('unexpected alpha or non-opaque native source pixels')
    return pix


def rgb_at(data:bytes,x:int,y:int)->tuple[int,int,int]:
    i=(y*W+x)*4
    return data[i+1],data[i+2],data[i+3]


def probes(path:Path,frames:tuple[int,...])->dict[int,dict[tuple[int,int],tuple[int,int,int,int]]]:
    out={}
    if path.is_symlink() or not path.is_file() or path.stat().st_size>100000:
        raise ValueError('missing or oversized original pixel palette probe table')
    with path.open('r',newline='') as inp:
        reader=csv.DictReader(inp,delimiter='\t')
        if reader.fieldnames!=['frame','x','y','r','g','b','palette_index']:
            raise ValueError('source palette probe schema mismatch')
        for row in reader:
            if None in row or any(v is None for v in row.values()):raise ValueError('truncated palette witness')
            f,x,y=[int(row[n]) for n in ('frame','x','y')]
            vals=tuple(int(row[n]) for n in ('r','g','b','palette_index'))
            if (f not in frames or (x,y) not in POINTS or (x,y) in out.get(f,{}) or
                    any(not 0<=i<=255 for i in vals)):
                raise ValueError('bad/duplicate/unsupported palette probe')
            out.setdefault(f,{})[(x,y)]=vals
    if any(set(out.get(f,{}))!=set(POINTS) for f in frames):
        raise ValueError('palette probes missing for sampled source frame')
    return out


def authenticated_frames(path:Path,field:str,marker:str,first:int,last:int)->set[int]:
    seen=set()
    with path.open('r',newline='') as stream:
        r=csv.DictReader(stream,delimiter='\t')
        if not r.fieldnames or field not in r.fieldnames or 'event' not in r.fieldnames:
            raise ValueError('source CPU/native witness table schema differs')
        for row in r:
            if row['event']==marker:
                f=int(row[field])
                if f in seen or not first<=f<=last:
                    raise ValueError('duplicate/outside frame anchor in private original source')
                seen.add(f)
    if seen !=set(range(first,last+1)):
        raise ValueError('original CPU/native frame witness coverage incomplete')
    return seen


def audit(root:Path,*,frames:tuple[int,...],palette_frames:tuple[int,...],cpu_sha:str,
          native_sha:str,first:int=380,last:int=640,explicit_hashes:dict[int,str]|None=None,
          sealed_cpu_sha:str|None=None,sealed_native_sha:str|None=None)->dict:
    if root.is_symlink() or not root.is_dir() or not frames or frames!=tuple(sorted(set(frames))):
        raise ValueError('incorrect or linked private source root/frame set')
    if any(not first<=f<=last for f in frames) or not set(palette_frames)<=set(frames):
        raise ValueError('source frame selection out of original capture')
    complete=root/'COMPLETE.txt'
    if complete.is_symlink() or not complete.is_file():raise ValueError('private source FM2 completion absent')
    marker=complete.read_text()
    if not all(s in marker.splitlines() for s in ('rom_identity_verified=yes','fm2_readonly=yes',
             f'first_frame={first}',f'last_frame={last}',f'frames={last-first+1}')):
        raise ValueError('source read-only movie completion marker differs')
    cpu=root/'stage335_ppu_latch_ram0d_events.tsv';native=root/'stage341_classic_refreshaddr.tsv'
    checked(cpu,cpu_sha);checked(native,native_sha)
    if sealed_cpu_sha is not None and cpu_sha!=sealed_cpu_sha:
        raise ValueError('same-session CPU differs from sealed Stage335 identity')
    if sealed_native_sha is not None and native_sha!=sealed_native_sha:
        raise ValueError('same-session native PPU differs from sealed Stage341 identity')
    authenticated_frames(cpu,'frame','frame_begin',first,last)
    authenticated_frames(native,'core_frame_ordinal','core_frame_start',first,last)
    pb=probes(root/'stage343_rgb_palette_probes.tsv',frames)
    raw_images={};unique_counts=[]; nonconstant=0
    indexed_ok=0
    for f in frames:
        gd=root/f'stage343_rgb_{f:04}.gd'
        if gd.is_symlink() or not gd.is_file():raise ValueError('original RGB frame missing')
        buf=gd.read_bytes();pix=parse_gd(buf)
        if explicit_hashes is not None:
            if f not in explicit_hashes:raise ValueError('missing owner-private frame digest')
            checked(gd,explicit_hashes[f],len(buf),len(buf))
        raw_images[f]=pix
        colors={pix[j+1:j+4] for j in range(0,len(pix),4)}
        unique_counts.append(len(colors))
        if len(colors)>1:nonconstant+=1
        for (x,y),v in pb[f].items():
            if rgb_at(pix,x,y)!=v[:3]:raise ValueError('original XBuf/GD RGB palette probe differs')
        idxfile=root/f'stage343_palette_{f:04}.idx'
        if f in palette_frames:
            if idxfile.is_symlink() or not idxfile.is_file() or idxfile.stat().st_size!=W*H:
                raise ValueError('indexed original palette plane missing or wrong dimensions')
            index_data=idxfile.read_bytes()
            for (x,y),v in pb[f].items():
                if index_data[y*W+x]!=v[3]:raise ValueError('source pixel palette index probe differs')
            indexed_ok+=1
        elif idxfile.exists():raise ValueError('unexpected unrequested palette source frame')
    diffs=[]
    for a,b in zip(frames,frames[1:]):
        im1,im2=raw_images[a],raw_images[b]
        changed=sum(im1[i+1:i+4]!=im2[i+1:i+4] for i in range(0,len(im1),4))
        diffs.append(changed)
    return {
      'format':'vpd_stage343_authenticated_original_rgb_frame_aggregate_v1',
      'source_window_frames':last-first+1,'authentic_sampled_rgb_frames':len(frames),
      'native_resolution_width':W,'native_resolution_height':H,
      'complete_indexed_palette_frame_count':indexed_ok,
      'original_rgb_pixel_count_verified':len(frames)*W*H,
      'source_rgb_palette_probe_matches':len(frames)*len(POINTS),
      'source_full_file_sha256_verified':True,
      'same_session_cpu_native_frame_anchors_verified':True,
      'cpu_witness_byte_identical_to_stage335':sealed_cpu_sha is not None and cpu_sha==sealed_cpu_sha,
      'native_witness_byte_identical_to_stage341':sealed_native_sha is not None and native_sha==sealed_native_sha,
      'sampled_frames_with_multiple_rgb_colors':nonconstant,
      'min_distinct_rgb_colors_per_frame':min(unique_counts),
      'max_distinct_rgb_colors_per_frame':max(unique_counts),
      'consecutive_sample_pairs_with_pixel_differences':sum(n>0 for n in diffs),
      'exact_hardware_ppu_dot_proven':False,
      'road_region_identified_or_geometry_proven':False,
      'effective_per_pixel_road_scroll_proven':False,
      'camera_speed_or_collision_proven':False,
      'raw_frame_or_palette_data_in_public_report':False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True,type=Path)
    p.add_argument('--cpu-sha256',required=True);p.add_argument('--native-sha256',required=True)
    p.add_argument('--sealed-cpu-sha256',required=True);p.add_argument('--sealed-native-sha256',required=True)
    p.add_argument('--frames',default='380,387,388,389,392,396,397,400,420,480,560,640')
    p.add_argument('--palette-frames',default='380,388,397,480')
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    parse=lambda x:tuple(int(y) for y in x.split(',') if y)
    try:
        obj=audit(a.root,frames=parse(a.frames),palette_frames=parse(a.palette_frames),
          cpu_sha=a.cpu_sha256,native_sha=a.native_sha256,
          sealed_cpu_sha=a.sealed_cpu_sha256,sealed_native_sha=a.sealed_native_sha256)
        data=json.dumps(obj,sort_keys=True,indent=2)+'\n'
        if a.output:
            if a.output.exists() or a.output.is_symlink():raise ValueError('refusing overwrite')
            a.output.write_text(data)
        else:print(data,end='')
    except (OSError,ValueError,UnicodeError,KeyError):p.exit(1,'VPD_STAGE343_ORIGINAL_RGB_WITNESS_INCONCLUSIVE\n')
if __name__=='__main__':main()
