#!/usr/bin/env python3
"""Stage352 preregistered original RGB holdout, four fixed environment subwindows.

These bands, boundaries, thresholds and offset search are frozen BEFORE owner
local FCEUX capture of frames 585-609. No adaptive tuning on this holdout.
An inconclusive candidate stays inconclusive, and a qualified disagreement
remains a disagreement; neither is silently filtered out.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import json
from pathlib import Path

import audit_private_stage344_motion as motion
import audit_private_stage345_scroll_motion as scroll
import audit_private_stage348_wide_displacement as wide
import audit_private_stage349_periodic_scroll as periodic

FIRST,LAST=585,609
LOCKED_REGIONS={
    'left_env_upper': (0,52,20,98),
    'left_env_lower': (0,52,98,175),
    'right_env_upper': (195,255,20,98),
    'right_env_lower': (195,255,98,175),
}
SIGNED_OFFSETS=tuple(range(-24,25))
MIN_RUNNER_GAP=0.045
MAX_RGB_MISMATCH=0.16


def qualify(a:bytes,b:bytes)->tuple[int|None,str]:
    if len(a)!=motion.WIDTH*motion.HEIGHT*3 or len(b)!=len(a):
        raise ValueError('not original native RGB format')
    found=set()
    for region in LOCKED_REGIONS.values():
        ranking=sorted((wide.mismatch(a,b,region,dy),dy) for dy in SIGNED_OFFSETS)
        best,runner=ranking[0],ranking[1]
        if best[0]>MAX_RGB_MISMATCH or runner[0]-best[0]<MIN_RUNNER_GAP:
            return None,'ambiguous_or_changed_scene'
        found.add(best[1])
    if len(found)!=1:
        return None,'independent_environment_masks_disagree'
    return found.pop(),'qualified'


def summarize(pairs:list[tuple[int|None,str,int|None]])->dict:
    if len(pairs)!=LAST-FIRST:
        raise ValueError('incomplete held-out consecutive RGB sequence')
    counts=Counter()
    observed=Counter()
    for shift,reason,periodic_step in pairs:
        if reason=='qualified':
            if type(shift) is not int or shift not in SIGNED_OFFSETS:
                raise ValueError('invalid original RGB selection')
            counts['qualified']+=1
            observed[shift]+=1
            if periodic_step is None:
                counts['ppu_scroll_invalid_or_unsupported']+=1
            elif shift==-periodic_step:
                counts['matching']+=1
            else:
                counts['contradictions']+=1
        elif shift is None and reason in (
            'ambiguous_or_changed_scene','independent_environment_masks_disagree'):
            counts['inconclusive']+=1
        else:
            raise ValueError('unknown confidence status')
    return {
       'format':'vpd_stage352_preregistered_environment_holdout_public_v1',
       'stage':352,
       'window':[FIRST,LAST],
       'native_resolution':[256,240],
       'preregistered_fixed_mask_count':len(LOCKED_REGIONS),
       'searched_signed_pixel_offsets':[min(SIGNED_OFFSETS),max(SIGNED_OFFSETS)],
       'preregistered_max_mismatch_fraction':MAX_RGB_MISMATCH,
       'preregistered_min_runner_gap_fraction':MIN_RUNNER_GAP,
       'original_rgb_frames_checked':25,
       'adjacent_pixel_pairs_total':24,
       'unambiguously_qualified_pairs':counts['qualified'],
       'qualified_mod240_scroll_matches':counts['matching'],
       'qualified_mod240_scroll_contradictions':counts['contradictions'],
       'qualified_but_unsupported_ppu_y_pairs':counts['ppu_scroll_invalid_or_unsupported'],
       'inconclusive_pixel_pairs':counts['inconclusive'],
       'pixel_displacement_distribution':{str(k):v for k,v in sorted(observed.items())},
       'masks_changed_after_source_observation':False,
       'general_vehicle_speed_camera_speed_road_collision_proven':False,
       'original_pixels_register_values_or_private_hashes_exposed':False,
    }


def audit(root:Path,manifest:Path,*,manifest_sha:str,cpu_pin:str,native_pin:str)->dict:
    if root.is_symlink() or not root.is_dir():
        raise ValueError('untrusted source directory')
    motion.checked(manifest,manifest_sha,min_size=500,max_size=20_000)
    m=json.loads(manifest.read_text(encoding='utf8'))
    if (m.get('format')!='vpd_stage344_original_consecutive_rgb_private_manifest_v1'
        or m.get('stage')!=352 or m.get('newppu')!=0
        or m.get('original_readonly') is not True
        or m.get('frames')!=list(range(FIRST,LAST+1))
        or m.get('palette_frames')!=[FIRST,(FIRST+LAST)//2,LAST]):
        raise ValueError('untrusted first-use private original capture manifest')
    expected=m['sha256']
    cpu=root/'stage335_ppu_latch_ram0d_events.tsv'
    ppu=root/'stage341_classic_refreshaddr.tsv'
    motion.checked(cpu,cpu_pin)
    motion.checked(ppu,native_pin)
    if expected.get(cpu.name)!=cpu_pin or expected.get(ppu.name)!=native_pin:
        raise ValueError('independent prior CPU/PPU seal mismatch')
    marker=root/'COMPLETE.txt'
    motion.checked(marker,expected[marker.name],min_size=30,max_size=10000)
    if not {'rom_identity_verified=yes','fm2_readonly=yes','frames=261',
            'first_frame=380','last_frame=640'}<=set(marker.read_text().splitlines()):
        raise ValueError('original read-only FM2 completion not proven')
    motion.verify_frame_anchors(cpu,'frame','frame_begin',380,640)
    motion.verify_frame_anchors(ppu,'core_frame_ordinal','core_frame_start',380,640)
    # Authentication of every selected original RGB/INDEX/probe file.
    frames={f:motion.read_frame(root/f'stage343_rgb_{f:04d}.gd',
             expected[f'stage343_rgb_{f:04d}.gd']) for f in range(FIRST,LAST+1)}
    if len(list(root.glob('stage343_rgb_*.gd')))!=25:
        raise ValueError('unexpected original frames in fresh private replay')
    probes=root/'stage343_rgb_palette_probes.tsv'
    motion.checked(probes,expected[probes.name])
    coverage=Counter();indices={}
    with probes.open(newline='') as stream:
        reader=csv.DictReader(stream,delimiter='\t')
        if reader.fieldnames!=['frame','x','y','r','g','b','palette_index']:
            raise ValueError('wrong RGB palette probe schema')
        for rec in reader:
            f,x,y=(int(rec[k]) for k in ('frame','x','y'))
            if f not in frames or (x,y) not in motion.POINTS or (f,x,y) in indices:
                raise ValueError('misaligned original palette probe')
            vals=[int(rec[k]) for k in ('r','g','b','palette_index')]
            if any(not 0<=v<=255 for v in vals):
                raise ValueError('invalid palette channel')
            pos=(y*motion.WIDTH+x)*3
            if frames[f][pos:pos+3]!=bytes(vals[:3]):
                raise ValueError('RGB and palette probe disagreement')
            coverage[f]+=1;indices[f,x,y]=vals[3]
    if any(coverage[f]!=len(motion.POINTS) for f in frames):
        raise ValueError('missing genuine RGB probe samples')
    for f in m['palette_frames']:
        name=f'stage343_palette_{f:04d}.idx'
        motion.checked(root/name,expected[name],min_size=61440,max_size=61440)
        plane=(root/name).read_bytes()
        if any(plane[y*256+x]!=indices[f,x,y] for x,y in motion.POINTS):
            raise ValueError('original palette plane mismatch')
    cc=scroll.original_rows(cpu,columns=scroll.CPU_HEADER,frame_column='frame',
                            first=FIRST,last=LAST)
    nn=scroll.original_rows(ppu,columns=scroll.NATIVE_HEADER,
              frame_column='core_frame_ordinal',first=FIRST,last=LAST)
    state=[scroll.frame_scroll(cc[f],nn[f]) for f in range(FIRST,LAST+1)]
    results=[]
    for frame in range(FIRST,LAST):
        shift,quality=qualify(frames[frame],frames[frame+1])
        left=state[frame-FIRST]['first_y'];right=state[frame-FIRST+1]['first_y']
        try:step=periodic.periodic_y_step(left,right)
        except ValueError:step=None
        results.append((shift,quality,step))
    report=summarize(results)
    report['sealed_source_cpu_and_classic_ppu_reproduced']=True
    report['all_150_original_rgb_palette_point_probes_match']=True
    report['three_full_original_palette_planes_match']=True
    report['private_manifest_pin_supplied_independently']=True
    return report


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True,type=Path)
    p.add_argument('--manifest',required=True,type=Path)
    p.add_argument('--sealed-manifest-sha256',required=True)
    p.add_argument('--sealed-cpu-sha256',required=True)
    p.add_argument('--sealed-native-sha256',required=True)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:
        payload=json.dumps(audit(a.root,a.manifest,
                manifest_sha=a.sealed_manifest_sha256,
                cpu_pin=a.sealed_cpu_sha256,
                native_pin=a.sealed_native_sha256),sort_keys=True,indent=2)+'\n'
        if a.output:
            if a.output.exists() or a.output.is_symlink():
                raise ValueError('owner-private report already exists')
            with a.output.open('x',encoding='utf8') as stream:stream.write(payload)
        else:print(payload,end='')
    except (OSError,ValueError,KeyError,TypeError,UnicodeError,json.JSONDecodeError):
        p.exit(1,'VPD_STAGE352_PREREGISTERED_HOLDOUT_INCONCLUSIVE\n')

if __name__=='__main__':main()
