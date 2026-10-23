#!/usr/bin/env python3
"""Stage350: independent out-of-sample original RGB vs modulo-240 PPU model.

Only owner-local checked source, no game pixels/ROM/FM2 in GitHub or CI.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path

import audit_private_stage349_periodic_scroll as prior

FIRST,LAST=520,544


def summarize(pairs:list[tuple[int,int,int]])->dict:
    if len(pairs)!=24:
        raise ValueError('missing adjacent original RGB pairs')
    shifts=Counter()
    signed8=0
    for step_240,step_8,display in pairs:
        if display not in (3,4):
            raise ValueError('out-of-sample original shift outside verified 3-4 pixel gate')
        if step_240!=-display:
            raise ValueError('modulo-240 model fails on original RGB pair')
        shifts[display]+=1
        signed8+=int(step_8==-display)
    if shifts[3]!=7 or shifts[4]!=17 or signed8!=24:
        raise ValueError('Stage350 original out-of-sample motion baseline differs')
    return {
       'format':'vpd_stage350_original_out_of_sample_modulo240_scroll_v1',
       'stage':350,
       'independently_authenticated_original_frame_window':[FIRST,LAST],
       'consecutive_original_rgb_frames':25,
       'adjacent_pixel_register_pairs':24,
       'four_masked_texture_bands_agree_for_each_pair':True,
       'original_display_shift_plus_three_pairs':shifts[3],
       'original_display_shift_plus_four_pairs':shifts[4],
       'first_vertical_scroll_modulo240_matches':24,
       'first_vertical_scroll_signed8_matches':signed8,
       'stage349_original_three_window_pairs_separately_verified':72,
       'four_window_combined_pairs_with_modulo240_agreement':96,
       'hardware_ppu_dot_proven':False,
       'other_levels_or_ppu_modes_proven':False,
       'camera_vehicle_speed_road_geometry_or_collision_proven':False,
       'original_game_pixels_raw_registers_or_private_sha_exposed':False,
    }


def audit(root:Path,manifest:Path,*,manifest_sha:str,
          cpu_pin:str,native_pin:str)->dict:
    pairs=prior.source_window(root,manifest,manifest_sha=manifest_sha,
        cpu_pin=cpu_pin,native_pin=native_pin,first=FIRST,last=LAST)
    return summarize(pairs)


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
        payload=json.dumps(result,indent=2,sort_keys=True)+'\n'
        if a.output:
            if a.output.is_symlink() or a.output.exists():
                raise ValueError('refusing overwrite')
            with a.output.open('x',encoding='utf8') as f:f.write(payload)
        else:print(payload,end='')
    except (OSError,ValueError,KeyError,TypeError,UnicodeError,json.JSONDecodeError):
        p.exit(1,'VPD_STAGE350_PRIVATE_OUT_OF_SAMPLE_INCONCLUSIVE\n')

if __name__=='__main__':main()
