#!/usr/bin/env python3
"""Stage349: three independently authenticated original RGB windows vs modulo-240 scroll.

This tests finite observed image/register correlations only. It never derives
camera/vehicle physics or NES PPU hardware dots. No game input in public CI.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path

import audit_private_stage344_motion as motion
import audit_private_stage345_scroll_motion as scroll

WINDOWS=((420,444),(445,469),(470,494))
VERTICAL_NAMETABLE_PIXELS=240


def periodic_y_step(before:int,after:int)->int:
    """Minimal signed 240-pixel step for conventional 0..239 vertical scrolling.

    Values 240..255 can address NES attribute rows and need independent
    analysis; do not silently coerce them into this conventional model.
    """
    if not isinstance(before,int) or isinstance(before,bool) or \
       not isinstance(after,int) or isinstance(after,bool) or \
       not (0<=before<VERTICAL_NAMETABLE_PIXELS and
            0<=after<VERTICAL_NAMETABLE_PIXELS):
        raise ValueError('scroll Y outside validated 0..239 cycle')
    difference=((after-before+120)%VERTICAL_NAMETABLE_PIXELS)-120
    if difference==-120:
        raise ValueError('ambiguous 120-pixel periodic displacement')
    return difference


def summarize(window_rows:list[tuple[int,int,list[int]]])->dict:
    if len(window_rows)!=3 or tuple((a,b) for a,b,_ in window_rows)!=WINDOWS:
        raise ValueError('three exact non-overlapping source windows required')
    counters=Counter()
    per_window=[]
    for first,last,pairs in window_rows:
        if len(pairs)!=24:
            raise ValueError('missing original adjacent image comparisons')
        subset=Counter()
        for step_240,step_256,pixels in pairs:
            if pixels not in (0,1,2):
                raise ValueError('unvalidated source RGB shift')
            if step_240!=-pixels:
                raise ValueError('periodic Y model contradicts original RGB')
            subset['periodic_match']+=1
            subset['unsigned_8bit_match']+=step_256==-pixels
            subset['visible_pixels_'+str(pixels)]+=1
            counters['all_pairs']+=1
            counters['periodic_match']+=1
            counters['signed_8bit_match']+=step_256==-pixels
            counters['pixel_'+str(pixels)]+=1
        per_window.append({'frames':[first,last],
            'original_adjacent_pairs':24,
            'modulo_240_image_matches':subset['periodic_match'],
            'signed_8bit_image_matches':subset['unsigned_8bit_match']})
    if (counters['all_pairs']!=72 or counters['periodic_match']!=72 or
        counters['signed_8bit_match']!=71 or counters['pixel_0']!=11 or
        counters['pixel_1']!=31 or counters['pixel_2']!=30):
        raise ValueError('prior authenticated three-window source baseline differs')
    return {
        'format':'vpd_stage349_original_rgb_periodic_240_scroll_v1',
        'stage':349,'consecutive_source_rgb_frames_verified':75,
        'independently_authenticated_source_windows':3,
        'adjacent_pixel_register_pairs_verified':72,
        'vertical_nametable_wrap_period_pixels':240,
        'modulo240_first_y_inverse_pixel_motion_matches':72,
        'ordinary_signed_8bit_first_y_inverse_pixel_motion_matches':71,
        'original_8bit_exception_reconciled_by_periodic_240_wrap':True,
        'image_shift_zero_pairs':11,
        'image_shift_plus_one_pairs':31,
        'image_shift_plus_two_pairs':30,
        'per_window':per_window,
        'attribute_row_out_of_range_y_values_proven_handled':False,
        'universal_game_camera_speed_model_proven':False,
        'vehicle_collision_or_road_geometry_proven':False,
        'actual_hardware_ppu_dot_proven':False,
        'source_game_pixels_or_register_bytes_disclosed':False,
    }


def source_window(root:Path,manifest:Path,*,manifest_sha:str,
                  cpu_pin:str,native_pin:str,first:int,last:int)->list[tuple[int,int,int]]:
    motion.checked(manifest,manifest_sha,min_size=100,max_size=20000)
    info=json.loads(manifest.read_text(encoding='utf-8'))
    if info.get('frames')!=list(range(first,last+1)) or info.get('newppu')!=0:
        raise ValueError('wrong original ROM-free source window/PPU mode')
    motion.audit(root,manifest,first=first,last=last,
        sealed_cpu_sha256=cpu_pin,sealed_native_sha256=native_pin)
    cpu=scroll.original_rows(root/'stage335_ppu_latch_ram0d_events.tsv',
        columns=scroll.CPU_HEADER,frame_column='frame',first=first,last=last)
    native=scroll.original_rows(root/'stage341_classic_refreshaddr.tsv',
        columns=scroll.NATIVE_HEADER,frame_column='core_frame_ordinal',
        first=first,last=last)
    samples=[scroll.frame_scroll(cpu[f],native[f]) for f in range(first,last+1)]
    frames={f:motion.read_frame(root/f'stage343_rgb_{f:04d}.gd',
            info['sha256'][f'stage343_rgb_{f:04d}.gd']) for f in range(first,last+1)}
    pairs=[]
    for f in range(first,last):
        choices={motion.score_band(frames[f],frames[f+1],band,name=name)[0]
                 for name,band in motion.BANDS.items()}
        if len(choices)!=1:
            raise ValueError('masked original RGB regions disagree')
        display=choices.pop()
        y0=samples[f-first]['first_y'];y1=samples[f-first+1]['first_y']
        pairs.append((periodic_y_step(y0,y1),scroll.signed_delta(y0,y1),display))
    return pairs


def audit(windows:list[tuple[int,int,Path,Path,str]],*,cpu_pin:str,native_pin:str)->dict:
    if len(windows)!=3 or tuple((a,b) for a,b,*_ in windows)!=WINDOWS:
        raise ValueError('wrong three owner-private window selections')
    reports=[]
    for first,last,root,manifest,manifest_sha in windows:
        reports.append((first,last,source_window(root,manifest,
             manifest_sha=manifest_sha,cpu_pin=cpu_pin,native_pin=native_pin,
             first=first,last=last)))
    return summarize(reports)


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--window',action='append',nargs=5,required=True,
          metavar=('FIRST','LAST','PRIVATE_ROOT','PRIVATE_MANIFEST','SEALED_MANIFEST_SHA256'))
    p.add_argument('--sealed-cpu-sha256',required=True)
    p.add_argument('--sealed-native-sha256',required=True)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:
        windows=[(int(first),int(last),Path(root),Path(manifest),sha)
                 for first,last,root,manifest,sha in a.window]
        result=audit(windows,cpu_pin=a.sealed_cpu_sha256,
                     native_pin=a.sealed_native_sha256)
        text=json.dumps(result,sort_keys=True,indent=2)+'\n'
        if a.output:
            if a.output.exists() or a.output.is_symlink():
                raise ValueError('do not overwrite previous private report')
            with a.output.open('x',encoding='utf-8') as f:f.write(text)
        else:print(text,end='')
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,json.JSONDecodeError):
        p.exit(1,'VPD_STAGE349_PRIVATE_PERIODIC_240_SCROLL_INCONCLUSIVE\n')

if __name__=='__main__':main()
