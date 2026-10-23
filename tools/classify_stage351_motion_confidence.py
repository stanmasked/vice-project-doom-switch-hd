#!/usr/bin/env python3
"""ROM-free Stage351 motion-evidence quality classifier.

Strict original Stage344 texture masks are preregistered. Alternative
non-overlapping environment submasks may explain ambiguity, but are exploratory
when selected after looking at original data; never promote them to the strict
four-band evidence class. This classifier DOES NOT authenticate gameplay input.
"""
from __future__ import annotations

PRIMARY=('left_environment','right_environment','left_marking','right_marking')
FOLLOWUP=('left_env_upper','left_env_lower','right_env_upper','right_env_lower')


def decision(scores:dict, *, followup:bool=False)->int|None:
    expected=FOLLOWUP if followup else PRIMARY
    if not isinstance(scores,dict) or set(scores)!=set(expected):
        raise ValueError('incomplete or unexpected candidate RGB bands')
    shifts=set()
    for name in expected:
        result=scores[name]
        if not isinstance(result,dict) or set(result)!={
             'best_shift','best_error_fraction','runner_gap_fraction'}:
            raise ValueError('malformed source-free band confidence summary')
        shift=result['best_shift']
        err=result['best_error_fraction']
        gap=result['runner_gap_fraction']
        if (type(shift) is not int or shift < -24 or shift > 24 or
            type(err) not in (int,float) or type(gap) not in (int,float) or
            not 0<=err<=1 or not 0<=gap<=1):
            raise ValueError('invalid RGB mismatch or shift score')
        marking=not followup and 'marking' in name
        if err > (.17 if marking else .16):
            return None
        if gap < (.008 if marking else .045):
            return None
        shifts.add(shift)
    return shifts.pop() if len(shifts)==1 else None


def classify(primary:list[dict],followup:list[dict],
             *,mod240_steps:list[int])->dict:
    if len(primary)!=24 or len(followup)!=24 or len(mod240_steps)!=24:
        raise ValueError('complete source-frame motion comparison required')
    strict=exploratory=unresolved=matches_strict=matches_secondary=0
    shifts={}
    for first,second,step in zip(primary,followup,mod240_steps):
        if type(step) is not int or not -119<=step<=119:
            raise ValueError('unsupported source-free modular delta')
        d=decision(first)
        if d is not None:
            strict+=1
            if d==-step:matches_strict+=1
            else:raise ValueError('original strict pixel/register contradiction')
            shifts[d]=shifts.get(d,0)+1
            continue
        e=decision(second,followup=True)
        if e is None:
            unresolved+=1
        elif e==-step:
            exploratory+=1
            matches_secondary+=1
            shifts[e]=shifts.get(e,0)+1
        else:
            raise ValueError('alternate masked pixel/register contradiction')
    if strict!=23 or exploratory!=1 or unresolved:
        raise ValueError('Stage351 evidence confidence baseline differs')
    if shifts!={0:5,2:2,3:1,5:15,8:1}:
        raise ValueError('source-free Stage351 displacement categories differ')
    return {
        'format':'vpd_stage351_source_free_two_gate_motion_confidence_v1',
        'stage':351,
        'frames_in_new_owner_private_capture':25,
        'adjacent_original_pixel_pairs':24,
        'preregistered_four_band_qualified_pairs':strict,
        'preregistered_four_band_mod240_matched_pairs':matches_strict,
        'adaptive_environment_submask_only_pairs':exploratory,
        'adaptive_environment_mod240_matched_pairs':matches_secondary,
        'remaining_inconclusive_pairs':unresolved,
        'observed_pixel_shift_counts':{str(k):v for k,v in sorted(shifts.items())},
        'fully_independent_four_band_confirmation_24_of_24':False,
        'adaptive_submask_evidence_requires_out_of_sample_retest':True,
        'general_game_camera_speed_or_vehicle_physics_proven':False,
    }
