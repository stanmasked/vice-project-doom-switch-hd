#!/usr/bin/env python3
"""Stage348: owner-local wide-range pixel-offset audit of one Stage347 anomaly.

Scans -24..+24 pixel offsets across independently masked original textures.
Never interprets a signed NES $2005 register change as physical camera speed.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import audit_private_stage344_motion as motion
import audit_private_stage345_scroll_motion as scroll
import audit_private_stage347_scroll_discontinuity as stage347

SHIFTS=tuple(range(-24,25))


def mismatch(a:bytes,b:bytes,band:tuple[int,int,int,int],dy:int)->float:
    if len(a)!=motion.WIDTH*motion.HEIGHT*3 or len(b)!=len(a):
        raise ValueError('invalid native RGB shape')
    x0,x1,y0,y1=band
    if not -24<=dy<=24 or not 0<=x0<x1<=motion.WIDTH or not 0<=y0<y1<=motion.HEIGHT:
        raise ValueError('unsupported original wide RGB texture window')
    start=max(y0,y0-dy);end=min(y1,y1-dy)
    if end<=start:raise ValueError('no source image overlap')
    bad=0
    for y in range(start,end):
        ia=(y*motion.WIDTH+x0)*3
        ib=((y+dy)*motion.WIDTH+x0)*3
        for x in range(x1-x0):
            i=ia+3*x;j=ib+3*x
            bad+=a[i:i+3]!=b[j:j+3]
    return bad/((end-start)*(x1-x0))


def wider_probe(a:bytes,b:bytes,band:tuple[int,int,int,int],*,name:str)->dict:
    ranks=sorted((mismatch(a,b,band,dy),dy) for dy in SHIFTS)
    best,runner=ranks[:2]
    min_gap=.008 if 'marking' in name else .045
    error_cutoff=.17 if 'marking' in name else .16
    if best[0]>error_cutoff or runner[0]-best[0]<min_gap:
        raise ValueError('flat, ambiguous or visually inconsistent wide shift')
    score_18=mismatch(a,b,band,18)
    return {
        'best_dy':best[1],
        'best_exact_match_fraction':1-best[0],
        'runner_up_gap':runner[0]-best[0],
        'wrong_18_shift_mismatch_fraction':score_18,
    }


def audit(root:Path,manifest:Path,*,manifest_sha:str,
          cpu_pin:str,native_pin:str)->dict:
    # Recheck the exact same 25 original frames/PPU and prior Stage347 baseline
    # before locating the one exceptional source register transition.
    earlier=stage347.audit(root,manifest,manifest_sha=manifest_sha,
                     cpu_pin=cpu_pin,native_pin=native_pin)
    m=json.loads(manifest.read_text(encoding='utf8'))
    first,last=stage347.FIRST,stage347.LAST
    cc=scroll.original_rows(root/'stage335_ppu_latch_ram0d_events.tsv',
           columns=scroll.CPU_HEADER,frame_column='frame',first=first,last=last)
    nn=scroll.original_rows(root/'stage341_classic_refreshaddr.tsv',
           columns=scroll.NATIVE_HEADER,frame_column='core_frame_ordinal',
           first=first,last=last)
    entries=[scroll.frame_scroll(cc[f],nn[f]) for f in range(first,last+1)]
    anomaly=[first+i for i,(a,b) in enumerate(zip(entries,entries[1:]))
             if scroll.signed_delta(a['first_y'],b['first_y'])==-18]
    if len(anomaly)!=1:
        raise ValueError('expected unique original source register discontinuity')
    f=anomaly[0]
    a=motion.read_frame(root/f'stage343_rgb_{f:04d}.gd',
                        m['sha256'][f'stage343_rgb_{f:04d}.gd'])
    b=motion.read_frame(root/f'stage343_rgb_{f+1:04d}.gd',
                        m['sha256'][f'stage343_rgb_{f+1:04d}.gd'])
    results=[wider_probe(a,b,band,name=name)
             for name,band in motion.BANDS.items()]
    if any(x['best_dy']!=2 or x['best_exact_match_fraction']!=1.0 or
           x['wrong_18_shift_mismatch_fraction']<.20 for x in results):
        raise ValueError('original wider RGB alternative contradicts evidence')
    return {
       'format':'vpd_stage348_private_wide_range_original_rgb_counterexample_v1',
       'stage':348,'source_frame_window':[first,last],
       'exceptional_adjacent_original_frame_pairs':1,
       'independently_masked_rgb_regions':len(results),
       'candidate_vertical_offsets_scanned_per_region':len(SHIFTS),
       'bounded_rgb_shift_selected_all_regions':2,
       'best_rgb_pixel_match_exact_in_all_regions':True,
       'alternate_plus_eighteen_shift_rejected_all_regions':True,
       'stage347_original_cpu_ppu_prior_seals_verified':
            earlier['same_session_original_cpu_ppu_seals_reproduced'],
       'hardware_ppu_dot_proven':False,
       'register_step_equivalent_to_camera_speed_proven':False,
       'original_rgb_register_values_or_hashes_exposed':False,
    }


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
        body=json.dumps(result,indent=2,sort_keys=True)+'\n'
        if a.output:
            if a.output.is_symlink() or a.output.exists():
                raise ValueError('do not overwrite sealed owner report')
            with a.output.open('x',encoding='utf8') as out:out.write(body)
        else:print(body,end='')
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,json.JSONDecodeError):
        p.exit(1,'VPD_STAGE348_ORIGINAL_WIDE_PIXEL_AUDIT_INCONCLUSIVE\n')

if __name__=='__main__':main()
