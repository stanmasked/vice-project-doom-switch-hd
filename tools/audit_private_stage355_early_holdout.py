#!/usr/bin/env python3
"""Stage355 pre-registered holdout: 3-of-4 robust environment score gate.

FROZEN BEFORE owner-local original frame window 380..404 is captured. This early source window precedes all previously captured native RGB windows and has not been examined by this image-audit protocol.
Identical Stage352 coordinates and fixed numerical confidence cutoffs.
A conflicting fourth strong region is a CONTRADICTION, never discarded.
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
import audit_private_stage352_preregistered_holdout as predecessor

FIRST,LAST=380,404
REGIONS=dict(predecessor.LOCKED_REGIONS)
OFFSETS=tuple(range(-24,25))
MAX_ERROR=.16
MIN_GAP=.045


def determine(scores:dict)->tuple[str,int|None]:
    """Predeclared confidence tiers from independent per-mask best/runner scores.

    Requires all 4 source regions; does not use scroll register prediction for
    selecting an RGB pixel shift. Three confident equal shifts with the fourth
    inconclusive qualifies in the prespecified 3-of-4 tier. Two incompatible
    confident shifts count as conflict, NOT as a match or an inconclusive repair.
    """
    if not isinstance(scores,dict) or set(scores)!=set(REGIONS):
        raise ValueError('four preregistered region scores required')
    confident=[]
    for name in REGIONS:
        rec=scores[name]
        if not isinstance(rec,(tuple,list)) or len(rec)!=3:
            raise ValueError('source RGB band score triplet absent')
        shift,err,gap=rec
        if (type(shift) is not int or shift not in OFFSETS or
            type(err) not in (int,float) or type(gap) not in (int,float) or
            not (0<=err<=1) or not (0<=gap<=1)):
            raise ValueError('malformed numeric RGB confidence')
        if err<=MAX_ERROR and gap>=MIN_GAP:confident.append(shift)
    if len(set(confident))>1:
        return 'qualified_mask_conflict',None
    if len(confident)==4:
        return 'strict_four_of_four',confident[0]
    if len(confident)==3:
        return 'independent_three_of_four',confident[0]
    return 'inconclusive_insufficient_masks',None


def summarize(pairs:list[tuple[str,int|None,int|None]])->dict:
    if len(pairs)!=24:raise ValueError('original holdout requires 24 adjacent samples')
    count=Counter();shifts=Counter()
    for tier,visual,step in pairs:
        if tier in ('strict_four_of_four','independent_three_of_four'):
            if type(visual) is not int or visual not in OFFSETS:
                raise ValueError('qualified original image lacks measured shift')
            count[tier]+=1
            shifts[visual]+=1
            if step is None:count['qualified_unsupported_register']+=1
            elif type(step) is not int or not -119<=step<=119:
                raise ValueError('unsupported modular scroll step shape')
            elif visual==-step:count['qualified_matches']+=1
            else:count['qualified_register_contradictions']+=1
        elif tier in ('qualified_mask_conflict','inconclusive_insufficient_masks'):
            if visual is not None:
                raise ValueError('nonqualified source pair has assigned displacement')
            if step is not None and (type(step) is not int or not -119<=step<=119):
                raise ValueError('unsupported modular scroll step shape')
            count[tier]+=1
        else:raise ValueError('unknown preregistered confidence tier')
    return {
        'format':'vpd_stage355_preregistered_three_of_four_holdout_public_v1',
        'stage':355,
        'original_frame_window':[FIRST,LAST],
        'original_rgb_frames':25,
        'original_adjacent_pairs':24,
        'locked_original_environment_mask_count':4,
        'minimum_confident_agreeing_masks':3,
        'candidate_vertical_shifts':[-24,24],
        'minimum_best_runner_confidence_gap':MIN_GAP,
        'maximum_best_rgb_mismatch_fraction':MAX_ERROR,
        'strict_four_of_four_pairs':count['strict_four_of_four'],
        'qualified_three_of_four_pairs':count['independent_three_of_four'],
        'conflicting_confident_mask_pairs':count['qualified_mask_conflict'],
        'inconclusive_insufficient_confident_masks':count['inconclusive_insufficient_masks'],
        'qualified_modulo240_matches':count['qualified_matches'],
        'qualified_modulo240_register_contradictions':count['qualified_register_contradictions'],
        'qualified_unsupported_register_pairs':count['qualified_unsupported_register'],
        'qualified_rgb_shift_distribution':{str(k):v for k,v in sorted(shifts.items())},
        'post_capture_roi_or_threshold_tuning_permitted':False,
        'general_vehicle_road_physics_or_hardware_ppu_dot_proven':False,
    }


def audit(root:Path,manifest:Path,*,manifest_sha:str,cpu_pin:str,native_pin:str)->dict:
    if root.is_symlink() or not root.is_dir():
        raise ValueError('invalid sealed original replay directory')
    motion.checked(manifest,manifest_sha,min_size=500,max_size=20000)
    m=json.loads(manifest.read_text(encoding='utf8'))
    if (m.get('format')!='vpd_stage344_original_consecutive_rgb_private_manifest_v1'
        or m.get('stage')!=355 or m.get('frames')!=list(range(FIRST,LAST+1))
        or m.get('original_readonly') is not True or m.get('newppu')!=0
        or m.get('palette_frames')!=[FIRST,(FIRST+LAST)//2,LAST]):
        raise ValueError('untrusted holdout source manifest')
    pins=m.get('sha256')
    if not isinstance(pins,dict):raise ValueError('missing sealed original member list')
    expected_names={'COMPLETE.txt','stage335_ppu_latch_ram0d_events.tsv',
                    'stage341_classic_refreshaddr.tsv',
                    'stage343_rgb_palette_probes.tsv'}
    expected_names.update(f'stage343_rgb_{f:04d}.gd' for f in range(FIRST,LAST+1))
    expected_names.update(f'stage343_palette_{f:04d}.idx' for f in (FIRST,(FIRST+LAST)//2,LAST))
    if set(pins)!=expected_names:raise ValueError('32 original member names differ')
    for name,pin in pins.items():
        motion.checked(root/name,pin)
    cpu=root/'stage335_ppu_latch_ram0d_events.tsv'
    native=root/'stage341_classic_refreshaddr.tsv'
    motion.checked(cpu,cpu_pin);motion.checked(native,native_pin)
    if pins[cpu.name]!=cpu_pin or pins[native.name]!=native_pin:
        raise ValueError('source trace seals not independently reproduced')
    marker=set((root/'COMPLETE.txt').read_text(encoding='utf8').splitlines())
    if not {'rom_identity_verified=yes','fm2_readonly=yes','frames=261',
             'first_frame=380','last_frame=640'}<=marker:
        raise ValueError('read-only original replay completion differs')
    motion.verify_frame_anchors(cpu,'frame','frame_begin',380,640)
    motion.verify_frame_anchors(native,'core_frame_ordinal','core_frame_start',380,640)
    frame_rgb={f:motion.read_frame(root/f'stage343_rgb_{f:04d}.gd',
                   pins[f'stage343_rgb_{f:04d}.gd']) for f in range(FIRST,LAST+1)}
    if len(list(root.glob('stage343_rgb_*.gd')))!=25:
        raise ValueError('unaccounted original RGB image files')
    probes={}
    path=root/'stage343_rgb_palette_probes.tsv'
    with path.open(newline='',encoding='utf8-sig') as stream:
        reader=csv.DictReader(stream,delimiter='\t')
        if reader.fieldnames!=['frame','x','y','r','g','b','palette_index']:
            raise ValueError('unexpected palette probe source schema')
        for r in reader:
            f,x,y=(int(r[k]) for k in ('frame','x','y'))
            values=[int(r[k]) for k in ('r','g','b','palette_index')]
            if (f not in frame_rgb or (x,y) not in motion.POINTS or
                (f,x,y) in probes or any(not 0<=v<=255 for v in values)):
                raise ValueError('unexpected original probe')
            offset=(y*256+x)*3
            if frame_rgb[f][offset:offset+3]!=bytes(values[:3]):
                raise ValueError('original RGB palette point disagreement')
            probes[f,x,y]=values[3]
    if len(probes)!=150:raise ValueError('150 original indexed probes not complete')
    for f in (FIRST,(FIRST+LAST)//2,LAST):
        plane=(root/f'stage343_palette_{f:04d}.idx').read_bytes()
        if len(plane)!=61440 or any(
            plane[y*256+x]!=probes[f,x,y] for x,y in motion.POINTS):
            raise ValueError('original full palette plane differs')
    c=scroll.original_rows(cpu,columns=scroll.CPU_HEADER,
                           frame_column='frame',first=FIRST,last=LAST)
    p=scroll.original_rows(native,columns=scroll.NATIVE_HEADER,
                           frame_column='core_frame_ordinal',first=FIRST,last=LAST)
    states=[scroll.frame_scroll(c[f],p[f]) for f in range(FIRST,LAST+1)]
    result=[]
    for i,f in enumerate(range(FIRST,LAST)):
        scores={}
        for name,rectangle in REGIONS.items():
            ranked=sorted((wide.mismatch(frame_rgb[f],frame_rgb[f+1],rectangle,dy),dy)
                          for dy in OFFSETS)
            (best,dy),runner=ranked[:2]
            scores[name]=(dy,best,runner[0]-best)
        tier,shift=determine(scores)
        left,right=states[i]['first_y'],states[i+1]['first_y']
        try:step=periodic.periodic_y_step(left,right)
        except ValueError:step=None
        result.append((tier,shift,step))
    report=summarize(result)
    report['original_source_32_member_sha_and_cpu_ppu_independent_seals_verified']=True
    report['original_150_rgb_palette_probes_and_3_full_planes_verified']=True
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
        payload=json.dumps(audit(a.root,a.manifest,manifest_sha=a.sealed_manifest_sha256,
                cpu_pin=a.sealed_cpu_sha256,native_pin=a.sealed_native_sha256),
                sort_keys=True,indent=2)+'\n'
        if a.output:
            if a.output.exists() or a.output.is_symlink():
                raise ValueError('cannot overwrite private result')
            with a.output.open('x',encoding='utf8') as out:out.write(payload)
        else:print(payload,end='')
    except (OSError,ValueError,KeyError,TypeError,UnicodeError,json.JSONDecodeError):
        p.exit(1,'VPD_STAGE355_PRIVATE_PREREGISTERED_HOLDOUT_INCONCLUSIVE\n')

if __name__=='__main__':main()
