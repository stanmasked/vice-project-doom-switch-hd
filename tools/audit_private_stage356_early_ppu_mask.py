#!/usr/bin/env python3
"""Stage356: ROM-free source-authorized diagnostic for a uniform early scene.

This analyzes already observed Stage355 (380-404) data; it is EXPLORATORY,
not a new held-out test, and never repairs the failed Stage355 motion gate.
Stage356 reports image repeat/flatness and mask/write *co-occurrence* only.
A zero PPU mask must not be inferred as the physical cause of every pixel.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import audit_private_stage344_motion as motion
import audit_private_stage345_scroll_motion as scroll

FIRST,LAST=380,404
POINTS=((0,0),(127,32),(128,120),(64,180),(192,200),(255,239))


def classify_images(frames:list[bytes], *, width:int=256,height:int=240)->dict:
    if len(frames)!=25 or type(width) is not int or type(height) is not int or not 1<=width<=256 or not 1<=height<=240:
        raise ValueError('exactly 25 uniformly sized source RGB frames required')
    size=width*height*3
    if any(type(f) is not bytes or len(f)!=size for f in frames):
        raise ValueError('malformed source RGB data')
    return {
        'original_native_rgb_frames':len(frames),
        'uniform_single_color_image_frames':sum(f==f[:3]*(width*height) for f in frames),
        'identical_consecutive_rgb_pairs':sum(a==b for a,b in zip(frames,frames[1:])),
        'unique_complete_rgb_frames':len(set(frames)),
    }


def classify_registers(per_frame:list[tuple[int,int]])->dict:
    """Each tuple is (CPU second-phase $2005 write count, native line0 mask).

    Integer PPU mask is a per-frame classic emulator witness, not a hardware
    dot-level measurement. We never infer an absent CPU write's byte value.
    """
    if len(per_frame)!=25 or any(
        type(w) is not int or type(mask) is not int or w<0 or mask<0 or mask>255
        for w,mask in per_frame):
        raise ValueError('25 valid original CPU/native PPU event counts required')
    missing=sum(w==0 for w,_ in per_frame)
    masked=sum(mask==0 for _,mask in per_frame)
    joint=sum(w==0 and mask==0 for w,mask in per_frame)
    return {
        'source_frames_without_second_phase_2005_write':missing,
        'source_frames_with_second_phase_2005_write':25-missing,
        'native_line_zero_ppu_mask_zero_frames':masked,
        'missing_second_phase_write_and_zero_line_mask_frames':joint,
        'missing_write_but_nonzero_line_mask_frames':missing-joint,
        'zero_line_mask_but_present_write_frames':masked-joint,
        'carried_previous_register_value_verified':False,
        'exact_physical_ppu_pixel_dot_verified':False,
    }


def summarize(images:dict,registers:dict)->dict:
    if images.get('original_native_rgb_frames')!=25:
        raise ValueError('partial source image witness')
    if (images.get('uniform_single_color_image_frames',0)>25 or
        images.get('identical_consecutive_rgb_pairs',0)>24):
        raise ValueError('invalid image evidence statistics')
    if registers.get('source_frames_without_second_phase_2005_write',-1)<0:
        raise ValueError('missing source write-count evidence')
    return {
        'format':'vpd_stage356_original_early_uniformity_mask_coincidence_v1',
        'stage':356,
        'source_original_frame_window':[FIRST,LAST],
        'evidence_provenance':'posthoc diagnostic on Stage355 originally held out FAILED gate',
        **images,**registers,
        'previous_stage355_motion_gate_passing':False,
        'frozen_stage355_four_mask_motion_result_changed':False,
        'automatic_zero_scroll_assumed_when_no_write':False,
        'camera_or_vehicle_physics_proven':False,
        'original_frames_trace_rows_or_private_hashes_in_output':False,
    }


def audit(root:Path,manifest:Path,*,manifest_sha:str,cpu_pin:str,native_pin:str)->dict:
    if root.is_symlink() or not root.is_dir() or manifest.is_symlink():
        raise ValueError('private authenticated source unavailable')
    motion.checked(manifest,manifest_sha,min_size=500,max_size=20_000)
    m=json.loads(manifest.read_text(encoding='utf8'))
    if (m.get('format')!='vpd_stage344_original_consecutive_rgb_private_manifest_v1'
        or m.get('stage')!=355 or m.get('frames')!=list(range(FIRST,LAST+1))
        or m.get('palette_frames')!=[380,392,404]
        or m.get('original_readonly') is not True or m.get('newppu')!=0):
        raise ValueError('unexpected owner-private original manifest')
    pins=m['sha256']
    expected={'COMPLETE.txt','stage335_ppu_latch_ram0d_events.tsv',
              'stage341_classic_refreshaddr.tsv','stage343_rgb_palette_probes.tsv'}
    expected.update(f'stage343_rgb_{f:04d}.gd' for f in range(FIRST,LAST+1))
    expected.update(f'stage343_palette_{f:04d}.idx' for f in (380,392,404))
    if set(pins)!=expected:raise ValueError('unexpected source manifest member list')
    for name,sha in pins.items():motion.checked(root/name,sha)
    if (pins['stage335_ppu_latch_ram0d_events.tsv']!=cpu_pin
        or pins['stage341_classic_refreshaddr.tsv']!=native_pin):
        raise ValueError('independent full original trace pins differ')
    marker=set((root/'COMPLETE.txt').read_text(encoding='utf8').splitlines())
    if not {'rom_identity_verified=yes','fm2_readonly=yes','frames=261',
            'first_frame=380','last_frame=640'}<=marker:
        raise ValueError('original read-only replay not completed')
    cpu=root/'stage335_ppu_latch_ram0d_events.tsv'
    native=root/'stage341_classic_refreshaddr.tsv'
    motion.verify_frame_anchors(cpu,'frame','frame_begin',380,640)
    motion.verify_frame_anchors(native,'core_frame_ordinal','core_frame_start',380,640)
    pixels=[motion.read_frame(root/f'stage343_rgb_{f:04d}.gd',
                 pins[f'stage343_rgb_{f:04d}.gd']) for f in range(FIRST,LAST+1)]
    c=scroll.original_rows(cpu,columns=scroll.CPU_HEADER,frame_column='frame',
                            first=FIRST,last=LAST)
    n=scroll.original_rows(native,columns=scroll.NATIVE_HEADER,
                            frame_column='core_frame_ordinal',first=FIRST,last=LAST)
    register_frames=[]
    for f in range(FIRST,LAST+1):
        cpu_rows=c[f];native_rows=n[f]
        second=sum(r['event']=='ppu_bus_write' and
                   r['ppu_toggle_before']=='1' for r in cpu_rows)
        line0=[r for r in native_rows if r['event']=='legacy_line_start' and
               r['legacy_scanline']=='0']
        if len(line0)!=1:raise ValueError('original native line0 anchor missing')
        mask_text=line0[0]['ppu_mask']
        if not mask_text.isdecimal():raise ValueError('invalid native mask witness')
        register_frames.append((second,int(mask_text)))
    stats=summarize(classify_images(pixels),classify_registers(register_frames))
    if (stats['uniform_single_color_image_frames']!=25 or
        stats['identical_consecutive_rgb_pairs']!=24 or
        stats['unique_complete_rgb_frames']!=1 or
        stats['source_frames_without_second_phase_2005_write']!=8 or
        stats['native_line_zero_ppu_mask_zero_frames']!=8 or
        stats['missing_second_phase_write_and_zero_line_mask_frames']!=8):
        raise ValueError('authenticated Stage355 exploratory source baseline changed')
    stats['all_32_authenticated_source_members_sha_verified']=True
    stats['cpu_and_classic_ppu_full_prior_seals_reproduced']=True
    return stats


def main():
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
             native_pin=a.sealed_native_sha256),indent=2,sort_keys=True)+'\n'
        if a.output:
            if a.output.exists() or a.output.is_symlink():
                raise ValueError('private diagnostic must not overwrite')
            with a.output.open('x',encoding='utf8') as out:out.write(payload)
        else:print(payload,end='')
    except (OSError,ValueError,KeyError,TypeError,UnicodeError,json.JSONDecodeError):
        p.exit(1,'VPD_STAGE356_DIAGNOSTIC_SOURCE_INCONCLUSIVE\n')


if __name__=='__main__':main()
