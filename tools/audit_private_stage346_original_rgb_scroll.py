#!/usr/bin/env python3
"""Stage346: owner-only authentic FCEUX RGB vs first classic PPU Y-scroll join.

Safe aggregate counts only. No original pixels, source hashes, CPU cycles,
register bytes, ROM, FM2 or raw trace rows may enter GitHub/CI.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path

import audit_private_stage344_motion as motion
import audit_private_stage345_scroll_motion as scroll

FIRST,LAST=445,469


def join(samples:list[dict],shifts:list[int])->dict:
    if len(samples)!=25 or len(shifts)!=24:
        raise ValueError('25 authentic frames and 24 adjacent comparisons required')
    if any(s.get('frame')!=FIRST+i for i,s in enumerate(samples)):
        raise ValueError('source frame order differs or duplicates a frame')
    movements=Counter()
    later_constant=0
    for before,after,shift in zip(samples,samples[1:],shifts):
        if shift not in (0,1,2,3,4):
            raise ValueError('unverified masked screen displacement range')
        step=scroll.signed_delta(before['first_y'],after['first_y'])
        if step!=-shift:
            raise ValueError('first $2005 register/image step disagree')
        movements[shift]+=1
        later_constant+=before['last_y']==after['last_y']
    if later_constant!=24:
        raise ValueError('later second $2005 phase changed during comparison')
    if sum(movements.values())!=24:
        raise ValueError('source pixel motion comparisons incomplete')
    return {
        'stage':346,
        'consecutive_original_rgb_frames':25,
        'adjacent_pixel_register_pairs_compared':24,
        'pixel_and_inverse_first_scroll_pairs_matched':24,
        'observed_image_shift_0_pairs':movements[0],
        'observed_image_shift_1_pairs':movements[1],
        'observed_image_shift_2_pairs':movements[2],
        'observed_image_shift_3_pairs':movements[3],
        'observed_image_shift_4_pairs':movements[4],
        'later_2005_y_constant_pairs':later_constant,
        'hardware_ppu_dot_proven':False,
        'camera_vehicle_speed_collision_proven':False,
    }


def private_audit(root:Path,manifest:Path, *,
                  manifest_sha:str,cpu_pin:str,native_pin:str)->dict:
    motion.checked(manifest,manifest_sha,min_size=100,max_size=20000)
    m=json.loads(manifest.read_text(encoding='utf-8'))
    if m.get('stage')!=346 or m.get('frames')!=list(range(FIRST,LAST+1)):
        raise ValueError('Stage346 source selection/provenance differs')
    stage344=motion.audit(root,manifest,first=FIRST,last=LAST,
                sealed_cpu_sha256=cpu_pin,sealed_native_sha256=native_pin)
    cpu=scroll.original_rows(root/'stage335_ppu_latch_ram0d_events.tsv',
           columns=scroll.CPU_HEADER,frame_column='frame',first=FIRST,last=LAST)
    native=scroll.original_rows(root/'stage341_classic_refreshaddr.tsv',
           columns=scroll.NATIVE_HEADER,frame_column='core_frame_ordinal',
           first=FIRST,last=LAST)
    samples=[{'frame':f,**scroll.frame_scroll(cpu[f],native[f])}
             for f in range(FIRST,LAST+1)]
    frames={f:motion.read_frame(root/f'stage343_rgb_{f:04d}.gd',
                   m['sha256'][f'stage343_rgb_{f:04d}.gd'])
            for f in range(FIRST,LAST+1)}
    shifts=[]
    for f in range(FIRST,LAST):
        decisions={motion.score_band(frames[f],frames[f+1],band,name=name)[0]
                   for name,band in motion.BANDS.items()}
        if len(decisions)!=1:
            raise ValueError('the four original non-HUD image areas disagree')
        shifts.append(decisions.pop())
    result=join(samples,shifts)
    # Both distinct provenance gates ran before joining the source bytes:
    # a new original-manifest SHA supplied from an independent private receipt,
    # and separately sealed prior Stage335/341 CPU/PPU SHA values.
    result.update({
       'format':'vpd_stage346_owner_local_authenticated_rgb_scroll_join_v1',
       'native_resolution':[256,240],
       'separate_texture_bands_consensus_per_pair':True,
       'independently_sampled_rgb_palette_matches':
          stage344['independent_rgb_sample_matches'],
       'full_original_palette_planes_verified':
          stage344['full_indexed_palette_frames_verified'],
       'source_cpu_native_traces_byte_identical_to_prior_seals':True,
       'first_scroll_matches_live_ram0d_and_native_temp_all_frames':True,
       'source_manifest_independently_pinned':True,
       'original_pixels_rom_fm2_hashes_exposed':False,
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
        result=private_audit(a.root,a.manifest,manifest_sha=a.sealed_manifest_sha256,
                             cpu_pin=a.sealed_cpu_sha256,native_pin=a.sealed_native_sha256)
        payload=json.dumps(result,indent=2,sort_keys=True)+'\n'
        if a.output:
            if a.output.exists() or a.output.is_symlink():
                raise ValueError('refuse overwrite of prior original source report')
            with a.output.open('x',encoding='utf-8') as stream:stream.write(payload)
        else:print(payload,end='')
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,json.JSONDecodeError):
        p.exit(1,'VPD_STAGE346_ORIGINAL_RGB_SCROLL_JOIN_INCONCLUSIVE\n')

if __name__=='__main__':main()
