#!/usr/bin/env python3
"""Owner-local Stage345: source-authenticated RGB displacement vs $2005/RAM $0D.

Never emit raw pixels, CPU/PPU values, original paths, timestamps or hashes.
Agreement in 25 source frames is not proof of camera or vehicle physics.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

import audit_private_stage344_motion as motion

CPU_HEADER = ('frame','sequence','cycle','event','pc','opcode','operand','value',
    'old_value','new_value','a','x','y','ppu_ordinal','ppu_toggle_before',
    'ppu_toggle_after','writer_cycle','writer_pc','writer_opcode','writer_operand',
    'ram0d_before','ram0d_live','bank_context','note')
NATIVE_HEADER = ('core_frame_ordinal','cpu_timestamp','event','legacy_scanline',
    'renderer_pixel_not_dot','refresh_addr','temp_addr','write_toggle','fine_x','ppu_mask')


def original_rows(path:Path, *, columns:tuple[str,...],frame_column:str,
                  first:int,last:int)->dict[int,list[dict[str,str]]]:
    result=defaultdict(list)
    with path.open('r',encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream,delimiter='\t')
        if reader.fieldnames!=list(columns):
            raise ValueError('original witness TSV schema differs')
        prior=-1
        for record in reader:
            if None in record or any(v is None for v in record.values()):
                raise ValueError('malformed source trace row')
            frame=int(record[frame_column])
            if frame<prior:raise ValueError('non-monotonic source witness frames')
            prior=frame
            if first<=frame<=last:result[frame].append(record)
    if set(result)!=set(range(first,last+1)):
        raise ValueError('required same-session source frame window incomplete')
    return result


def hex_byte(value:str)->int:
    if len(value)!=2 or any(c not in '0123456789abcdefABCDEF' for c in value):
        raise ValueError('invalid source vertical register byte')
    return int(value,16)


def hex_word(value:str)->int:
    if len(value)!=4 or any(c not in '0123456789abcdefABCDEF' for c in value):
        raise ValueError('invalid classic PPU temporary address')
    return int(value,16)


def vertical_from_temp(t:int)->int:
    return ((t>>12)&7)|(((t>>5)&31)<<3)


def frame_scroll(cpu_rows:list[dict[str,str]],native_rows:list[dict[str,str]])->dict:
    first=[r for r in cpu_rows if r['event']=='ppu_bus_write' and r['ppu_toggle_before']=='1']
    line0=[r for r in native_rows if r['event']=='legacy_line_start' and r['legacy_scanline']=='0']
    anchors=[r for r in cpu_rows if r['event']=='frame_begin']
    ends=[r for r in cpu_rows if r['event']=='frame_end']
    starts=[r for r in native_rows if r['event']=='core_frame_start']
    if len(first)<1 or len(line0)!=1 or len(anchors)!=1 or len(ends)!=1 or len(starts)!=1:
        raise ValueError('original CPU/PPU source scroll/frame anchors incomplete')
    if cpu_rows[0] is not anchors[0] or native_rows[0] is not starts[0]:
        raise ValueError('original CPU/PPU event ordering differs')
    value=hex_byte(first[0]['value'])
    if hex_byte(first[0]['ram0d_live'])!=value:
        raise ValueError('first second-phase $2005 not equal to live RAM $0D')
    if vertical_from_temp(hex_word(line0[0]['temp_addr']))!=value:
        raise ValueError('classic PPU line-zero temporary Y differs from first $2005')
    base=int(anchors[0]['cycle'])
    first_clock=int(first[0]['cycle'])
    line_clock=base+int(line0[0]['cpu_timestamp'])
    if base<0 or not base<=first_clock<line_clock:
        raise ValueError('first vertical scroll register write not before native line zero')
    if any(r['event'] in ('W2006','ppu_bus_write') and
           first_clock<int(r['cycle'])<line_clock for r in cpu_rows):
        raise ValueError('intervening temporary PPU address write')
    return {'first_y':value,'last_y':hex_byte(first[-1]['value']),
            'ram_writes':sum(r['event']=='ram0d_bus_write' for r in cpu_rows)}


def signed_delta(before:int,after:int)->int:
    if not 0<=before<=255 or not 0<=after<=255:
        raise ValueError('invalid vertical register sample')
    return ((after-before+128)%256)-128


def correlate(samples:list[dict],shifts:list[int])->dict:
    if len(samples)!=25 or len(shifts)!=24:
        raise ValueError('unsupported original consecutive evidence length')
    if any(s['frame']!=420+i for i,s in enumerate(samples)):
        raise ValueError('non-consecutive original frame order')
    counts=Counter()
    last_stable=0
    for i,shift in enumerate(shifts):
        if shift not in (0,1):
            raise ValueError('source motion outside observed bounded gate')
        a,b=samples[i],samples[i+1]
        delta=signed_delta(a['first_y'],b['first_y'])
        if delta!=-shift:
            raise ValueError('native image displacement / first $2005 mismatch')
        counts[(shift,delta)]+=1
        last_stable+=a['last_y']==b['last_y']
    if counts[(0,0)]!=11 or counts[(1,-1)]!=13:
        raise ValueError('original Stage344 visual displacement baseline differs')
    if last_stable!=24:
        raise ValueError('later $2005 phase is not independently constant')
    return {
        'format':'vpd_stage345_original_rgb_classic_scroll_correlation_public_v1',
        'stage':345,
        'consecutive_authenticated_frames':25,
        'adjacent_pairs':24,
        'all_four_stage344_visual_bands_consensus':True,
        'display_zero_and_first_2005_y_unchanged_pairs':counts[(0,0)],
        'display_plus_one_and_first_2005_y_minus_one_pairs':counts[(1,-1)],
        'display_vs_first_2005_comparisons_matching':24,
        'later_2005_y_unchanged_adjacent_pairs':last_stable,
        'original_frame_cpu_ppu_identity_reauthenticated':True,
        'first_2005_equals_live_ram0d_all_selected_frames':True,
        'first_2005_equals_native_classic_line0_t_all_selected_frames':True,
        'hardware_ppu_dot_proven':False,
        'general_camera_speed_proven':False,
        'road_geometry_or_vehicle_physics_proven':False,
        'raw_register_values_or_original_pixels_disclosed':False,
    }


def audit(root:Path,manifest:Path,*,cpu_pin:str,native_pin:str)->dict:
    first,last=motion.FIRST,motion.LAST
    motion.audit(root,manifest,sealed_cpu_sha256=cpu_pin,
                 sealed_native_sha256=native_pin,first=first,last=last)
    m=json.loads(manifest.read_text(encoding='utf8'))
    cpu=original_rows(root/'stage335_ppu_latch_ram0d_events.tsv',columns=CPU_HEADER,
                      frame_column='frame',first=first,last=last)
    native=original_rows(root/'stage341_classic_refreshaddr.tsv',columns=NATIVE_HEADER,
                         frame_column='core_frame_ordinal',first=first,last=last)
    samples=[];shifts=[]
    for f in range(first,last+1):
        samples.append({'frame':f,**frame_scroll(cpu[f],native[f])})
    for f in range(first,last):
        x=motion.read_frame(root/f'stage343_rgb_{f:04d}.gd',
                            m['sha256'][f'stage343_rgb_{f:04d}.gd'])
        y=motion.read_frame(root/f'stage343_rgb_{f+1:04d}.gd',
                            m['sha256'][f'stage343_rgb_{f+1:04d}.gd'])
        decisions={motion.score_band(x,y,band,name=name)[0]
                   for name,band in motion.BANDS.items()}
        if len(decisions)!=1:
            raise ValueError('independently masked RGB motion bands disagree')
        shifts.append(decisions.pop())
    summary=correlate(samples,shifts)
    summary['selected_frames_with_ram0d_bus_writes']=sum(x['ram_writes']>0 for x in samples)
    summary['selected_frames_with_no_ram0d_bus_writes']=sum(x['ram_writes']==0 for x in samples)
    return summary


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True,type=Path)
    p.add_argument('--manifest',required=True,type=Path)
    p.add_argument('--sealed-cpu-sha256',required=True)
    p.add_argument('--sealed-native-sha256',required=True)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:
        result=audit(a.root,a.manifest,cpu_pin=a.sealed_cpu_sha256,
                     native_pin=a.sealed_native_sha256)
        payload=json.dumps(result,indent=2,sort_keys=True)+'\n'
        if a.output:
            if a.output.exists() or a.output.is_symlink():
                raise ValueError('do not overwrite prior owner-private report')
            with a.output.open('x',encoding='utf8') as out:out.write(payload)
        else:print(payload,end='')
    except (OSError,ValueError,KeyError,TypeError,UnicodeError,json.JSONDecodeError):
        p.exit(1,'VPD_STAGE345_ORIGINAL_SCROLL_PIXEL_CORRELATION_INCONCLUSIVE\n')
if __name__=='__main__':main()
