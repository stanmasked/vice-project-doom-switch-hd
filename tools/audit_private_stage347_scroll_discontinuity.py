#!/usr/bin/env python3
"""Stage347 owner-only original RGB/classic $2005 discontinuity verifier.

Original CPU/PPU traces and frame RGB remain owner-private. Unlike Stage345,
a mismatch is an observed result to count, not evidence to silently discard.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path

import audit_private_stage344_motion as motion
import audit_private_stage345_scroll_motion as scroll

FIRST,LAST=470,494


def compare(samples:list[dict],shifts:list[int])->dict:
    if len(samples)!=25 or len(shifts)!=24:
        raise ValueError('complete original 25-frame/24-pair window required')
    if any(x.get('frame')!=FIRST+i for i,x in enumerate(samples)):
        raise ValueError('original frame window not consecutive')
    accepted=Counter()
    phase_stable=0
    for a,b,display in zip(samples,samples[1:],shifts):
        if display not in motion.SHIFTS:
            raise ValueError('new original visual shift outside measured mask search')
        step=scroll.signed_delta(a['first_y'],b['first_y'])
        if display!=-step:
            accepted['disagreements']+=1
            if not (display==2 and step==-18):
                raise ValueError('unrecognized discontinuity, not source-backed')
            accepted['minus_eighteen_y_plus_two_pixels']+=1
        else:
            accepted['matches']+=1
        accepted['display_shift_two']+=display==2
        phase_stable+=a['last_y']==b['last_y']
    if phase_stable!=24:
        raise ValueError('unexpected later $2005 Y phase change')
    if (accepted['matches']!=23 or accepted['disagreements']!=1 or
        accepted['minus_eighteen_y_plus_two_pixels']!=1 or
        accepted['display_shift_two']!=24):
        raise ValueError('original Stage347 bounded baseline differed')
    return {
       'stage':347,
       'source_frame_window':[FIRST,LAST],
       'consecutive_original_rgb_frames':25,
       'adjacent_pairs':24,
       'background_pixel_shift_two_pairs':24,
       'first_scroll_inverse_motion_agree_pairs':23,
       'first_scroll_inverse_motion_disagree_pairs':1,
       'register_minus_eighteen_image_plus_two_exceptions':1,
       'later_scroll_y_constant_pairs':phase_stable,
       'universal_register_pixel_displacement_law_supported':False,
       'camera_vehicle_speed_or_collision_proven':False,
       'independent_hardware_ppu_dot_proven':False,
    }


def audit(root:Path,manifest:Path,*,manifest_sha:str,cpu_pin:str,native_pin:str)->dict:
    motion.checked(manifest,manifest_sha,min_size=100,max_size=20000)
    m=json.loads(manifest.read_text(encoding='utf8'))
    if m.get('stage')!=347 or m.get('frames')!=list(range(FIRST,LAST+1)):
        raise ValueError('untrusted Stage347 owner-private source selection')
    rgb=motion.audit(root,manifest,first=FIRST,last=LAST,
             sealed_cpu_sha256=cpu_pin,sealed_native_sha256=native_pin)
    cc=scroll.original_rows(root/'stage335_ppu_latch_ram0d_events.tsv',
          columns=scroll.CPU_HEADER,frame_column='frame',first=FIRST,last=LAST)
    nn=scroll.original_rows(root/'stage341_classic_refreshaddr.tsv',
          columns=scroll.NATIVE_HEADER,frame_column='core_frame_ordinal',
          first=FIRST,last=LAST)
    samples=[{'frame':f,**scroll.frame_scroll(cc[f],nn[f])}
             for f in range(FIRST,LAST+1)]
    images={f:motion.read_frame(root/f'stage343_rgb_{f:04d}.gd',
            m['sha256'][f'stage343_rgb_{f:04d}.gd'])
            for f in range(FIRST,LAST+1)}
    shifts=[]
    for f in range(FIRST,LAST):
        choices={motion.score_band(images[f],images[f+1],band,name=name)[0]
                 for name,band in motion.BANDS.items()}
        if len(choices)!=1:
            raise ValueError('four masked original RGB areas disagree')
        shifts.append(choices.pop())
    result=compare(samples,shifts)
    result.update({
       'format':'vpd_stage347_owner_private_original_rgb_register_exception_v1',
       'native_resolution':[256,240],
       'source_rgb_and_register_manifest_independently_sha_pinned':True,
       'same_session_original_cpu_ppu_seals_reproduced':True,
       'four_independent_background_regions_consensus':True,
       'independent_original_rgb_palette_samples':
           rgb['independent_rgb_sample_matches'],
       'full_original_indexed_palette_planes':
           rgb['full_indexed_palette_frames_verified'],
       'first_scroll_ram0d_native_temp_join_verified':True,
       'original_pixels_rom_fm2_raw_registers_exposed':False,
    })
    return result


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
        result=audit(a.root,a.manifest,manifest_sha=a.sealed_manifest_sha256,
                   cpu_pin=a.sealed_cpu_sha256,native_pin=a.sealed_native_sha256)
        body=json.dumps(result,sort_keys=True,indent=2)+'\n'
        if a.output:
            if a.output.is_symlink() or a.output.exists():
                raise ValueError('refuse overwrite')
            with a.output.open('x',encoding='utf8') as f:f.write(body)
        else:print(body,end='')
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,json.JSONDecodeError):
        p.exit(1,'VPD_STAGE347_PRIVATE_DISCONTINUITY_INCONCLUSIVE\n')

if __name__=='__main__':main()
