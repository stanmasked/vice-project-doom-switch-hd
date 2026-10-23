#!/usr/bin/env python3
"""Stage346 owner-private FCEUX trace reconnaissance; produces counts, not gameplay.

A CPU-register step does not establish rendered motion or vehicle/camera speed.
No original input data is accepted in ROM-free public CI.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path

import audit_private_stage344_motion as motion
import audit_private_stage345_scroll_motion as scroll

WINDOWS = ((445,469),(470,494),(520,544),(560,584))
SOURCE_FIRST, SOURCE_LAST = 380,640


def classify(delta:int)->str:
    if delta==0:return 'unchanged'
    if delta==-1:return 'minus_one'
    if delta==-2:return 'minus_two'
    if delta in (-3,-4):return 'minus_three_or_four'
    if -128<=delta<=-5:return 'minus_five_or_more'
    if 1<=delta<=127:return 'positive_step'
    raise ValueError('invalid modular scroll delta')


def profile(samples:list[dict], *, first:int,last:int)->dict:
    if (first,last) not in WINDOWS or len(samples)!=25:
        raise ValueError('unsupported owner-private trace profile window')
    if any(s.get('frame')!=first+i for i,s in enumerate(samples)):
        raise ValueError('missing, reordered or duplicate original frame')
    counts=Counter()
    later_stable=0
    for prev,nxt in zip(samples,samples[1:]):
        d=scroll.signed_delta(prev['first_y'],nxt['first_y'])
        counts[classify(d)]+=1
        later_stable+=prev['last_y']==nxt['last_y']
    if sum(counts.values())!=24:
        raise ValueError('incomplete private window transition coverage')
    if later_stable!=24:
        raise ValueError('later source scroll phase changed in selected interval')
    return {
        'source_window':[first,last],
        'verified_cpu_native_first_scroll_frames':25,
        'adjacent_register_pairs':24,
        'first_scroll_deltas_classified':{name:counts[name] for name in (
          'unchanged','minus_one','minus_two','minus_three_or_four',
          'minus_five_or_more','positive_step')},
        'later_scroll_phase_constant_pairs':later_stable,
        'frames_with_ram0d_writes':sum(x['ram_writes']>0 for x in samples),
        'native_rgb_frames_in_this_window_verified':0,
        'rgb_scroll_displacement_generalization_proven':False,
    }


def private_audit(cpu:Path,native:Path,complete:Path, *,
                  cpu_sha:str,native_sha:str,complete_sha:str)->dict:
    motion.checked(cpu,cpu_sha)
    motion.checked(native,native_sha)
    motion.checked(complete,complete_sha,min_size=30,max_size=10000)
    marker=set(complete.read_text(encoding='utf8').splitlines())
    expected={'rom_identity_verified=yes','fm2_readonly=yes',
              'frames=261','first_frame=380','last_frame=640'}
    if not expected<=marker:
        raise ValueError('prior source replay completion marker differs')
    motion.verify_frame_anchors(cpu,'frame','frame_begin',SOURCE_FIRST,SOURCE_LAST)
    motion.verify_frame_anchors(native,'core_frame_ordinal','core_frame_start',
                                SOURCE_FIRST,SOURCE_LAST)
    cpu_by_frame=scroll.original_rows(cpu,columns=scroll.CPU_HEADER,
                           frame_column='frame',first=SOURCE_FIRST,last=SOURCE_LAST)
    native_by_frame=scroll.original_rows(native,columns=scroll.NATIVE_HEADER,
                           frame_column='core_frame_ordinal',first=SOURCE_FIRST,last=SOURCE_LAST)
    profiles=[]
    for first,last in WINDOWS:
        samples=[{'frame':frame,**scroll.frame_scroll(cpu_by_frame[frame],
                  native_by_frame[frame])} for frame in range(first,last+1)]
        profiles.append(profile(samples,first=first,last=last))
    return {
        'format':'vpd_stage346_private_cpu_ppu_scroll_window_preflight_v1',
        'stage':346,
        'authenticated_previous_source_frame_window':[SOURCE_FIRST,SOURCE_LAST],
        'selected_source_trace_windows':len(profiles),
        'selected_original_register_frames_verified':sum(
            p['verified_cpu_native_first_scroll_frames'] for p in profiles),
        'source_pins_and_readonly_completion_verified':True,
        'original_new_rgb_capture_performed':False,
        'per_window_preflight':profiles,
        'source_register_step_is_not_physical_camera_speed':True,
        'hardware_ppu_dot_observed':False,
        'original_private_events_or_hashes_exposed':False,
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cpu',type=Path,required=True)
    p.add_argument('--native',type=Path,required=True)
    p.add_argument('--complete',type=Path,required=True)
    p.add_argument('--sealed-cpu-sha256',required=True)
    p.add_argument('--sealed-native-sha256',required=True)
    p.add_argument('--sealed-complete-sha256',required=True)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:
        result=private_audit(a.cpu,a.native,a.complete,
          cpu_sha=a.sealed_cpu_sha256,native_sha=a.sealed_native_sha256,
          complete_sha=a.sealed_complete_sha256)
        payload=json.dumps(result,indent=2,sort_keys=True)+'\n'
        if a.output:
            if a.output.exists() or a.output.is_symlink():
                raise ValueError('refuse to overwrite evidence report')
            with a.output.open('x',encoding='utf8') as out:out.write(payload)
        else:print(payload,end='')
    except (OSError,ValueError,KeyError,TypeError,UnicodeError,json.JSONDecodeError):
        p.exit(1,'VPD_STAGE346_PRIVATE_TRACE_PREFLIGHT_INCONCLUSIVE\n')

if __name__=='__main__':main()
