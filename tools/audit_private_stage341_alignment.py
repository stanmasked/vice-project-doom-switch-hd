#!/usr/bin/env python3
"""Independently match native *classic-core* $2006 state to same-session FM2 CPU trace.

Accepts only private paths; outputs aggregate counts and verdicts. This tool
proves frame/CPU-write alignment for the sampled window, not per-dot scroll.
Never copy original ROMs, FM2s, CPU timestamps or PPU addresses into GitHub.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path

NATIVE_HEADER=('core_frame_ordinal','cpu_timestamp','event','legacy_scanline','renderer_pixel_not_dot','refresh_addr','temp_addr','write_toggle','fine_x','ppu_mask')
CPU_COLS={'frame','event','value','ppu_toggle_before'}
MAX_BYTES=80_000_000


def sha256(p:Path)->str:
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def protected_file(p:Path,sha:str)->None:
    if p.is_symlink() or not p.is_file() or not 0<p.stat().st_size<=MAX_BYTES:
        raise ValueError('private input missing or outside size boundary')
    if not sha or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):
        raise ValueError('expected private SHA-256 required')
    if sha256(p)!=sha:raise ValueError('authenticated private source bytes differ')


def analyze(cpu:Path,native:Path,complete:Path, *, cpu_sha:str,native_sha:str,
            first:int=380,last:int=640,require_stage335:bool=True)->dict:
    if not 0<=first<=last<=100000 or last-first>1000:raise ValueError('bad frame window')
    protected_file(cpu,cpu_sha); protected_file(native,native_sha)
    if complete.is_symlink() or not complete.is_file():raise ValueError('no private read-only completion witness')
    marker=complete.read_text(encoding='utf-8')
    for s in ('rom_identity_verified=yes','fm2_readonly=yes',
              'first_frame='+str(first),'last_frame='+str(last),
              'frames='+str(last-first+1)):
        if s not in marker.splitlines():raise ValueError('private completion marker does not authenticate session')
    cpu_by_frame=defaultdict(list); native_by_frame=defaultdict(list)
    pending={}; cpu_writes=0; frame_seen=set(); prev_native=None; native_markers=defaultdict(int)
    with cpu.open('r',encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f,delimiter='\t')
        if reader.fieldnames is None or not CPU_COLS.issubset(reader.fieldnames):
            raise ValueError('invalid same-session CPU trace header')
        for row in reader:
            if None in row or any(v is None for v in row.values()):raise ValueError('corrupt CPU event row')
            frame=int(row['frame']);
            if not first<=frame<=last:raise ValueError('CPU frame outside declared window')
            frame_seen.add(frame)
            if row['event']!='W2006':continue
            cpu_writes+=1;toggle=row['ppu_toggle_before']; value=row['value']
            if len(value)!=2 or any(c not in '0123456789abcdefABCDEF' for c in value):
                raise ValueError('invalid original CPU bus value')
            value=int(value,16)
            if toggle=='0':
                if frame in pending:raise ValueError('unpaired CPU PPUADDR high write')
                pending[frame]=value
            elif toggle=='1':
                if frame not in pending:raise ValueError('unpaired CPU PPUADDR low write')
                cpu_by_frame[frame].append(((pending.pop(frame)&0x3f)<<8)|value)
            else:raise ValueError('unexpected shared write toggle')
    if pending:raise ValueError('incomplete original CPU PPUADDR pair')
    if frame_seen !=set(range(first,last+1)):raise ValueError('source frame coverage missing')
    if require_stage335 and (first,last)!=(380,640):raise ValueError('Stage335 window must remain 380–640')
    if require_stage335 and (cpu_writes!=6096 or sum(map(len,cpu_by_frame.values()))!=3048):
        raise ValueError('Stage335 PPUADDR aggregate baseline mismatch')
    with native.open('r',encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f,delimiter='\t')
        if reader.fieldnames!=list(NATIVE_HEADER):raise ValueError('classic-core trace schema differs')
        for row in reader:
            if None in row or any(v is None for v in row.values()):raise ValueError('truncated native event row')
            frame=int(row['core_frame_ordinal']); tick=int(row['cpu_timestamp'])
            if not first<=frame<=last or tick<0:raise ValueError('native event out of capture window')
            if prev_native is not None and (frame<prev_native[0] or (frame==prev_native[0] and tick<prev_native[1])):
                raise ValueError('native event order nonmonotonic')
            prev_native=(frame,tick)
            if row['event']=='core_frame_start':native_markers[frame]+=1
            elif row['event']=='cpu_second_2006':
                raw=row['refresh_addr']
                if len(raw)!=4 or any(c not in '0123456789abcdefABCDEF' for c in raw):
                    raise ValueError('invalid native PPUADDR')
                native_by_frame[frame].append(int(raw,16)&0x3fff)
    if any(native_markers[f]!=1 for f in range(first,last+1)):
        raise ValueError('missing or duplicate native core-frame marker')
    n_native=sum(map(len,native_by_frame.values()));n_cpu=sum(map(len,cpu_by_frame.values()))
    if n_native!=n_cpu:raise ValueError('native and CPU second-write totals differ')
    if any(native_by_frame[f]!=cpu_by_frame[f] for f in range(first,last+1)):
        raise ValueError('same-frame, same-order full PPU address mismatch')
    # An offset match on some coincident frames is not equivalent to full alignment.
    def offset_matches(shift:int)->bool:
        frames=[f for f in range(first,last+1) if first<=f+shift<=last]
        return bool(frames) and all(native_by_frame[f]==cpu_by_frame[f+shift] for f in frames)
    if any(offset_matches(shift) for shift in (-2,-1,1,2)):
        raise ValueError('frame alignment ambiguous under +/-2 neighboring shifts')
    return {
        'format':'vpd_stage341_private_same_session_core_ppu_alignment_v1',
        'core_and_fm2_frames_compared':last-first+1,
        'cpu_2006_total':cpu_writes,
        'cpu_2006_second_writes':n_cpu,
        'native_classic_2006_second_writes':n_native,
        'full_ppu_address_matches':n_cpu,
        'full_ppu_address_mismatches':0,
        'same_session_movie_core_frame_alignment_verified':True,
        'source_readonly_completion_marker_verified':True,
        'neighboring_frame_offsets_ambiguous':False,
        'authentic_legacy_refreshaddr_events_captured':True,
        'independent_ppu_dot_phase_observed':False,
        'effective_rendered_scroll_proven':False,
        'road_geometry_proven':False,
        'private_ppu_addresses_exposed':False,
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cpu',required=True,type=Path);p.add_argument('--native',required=True,type=Path)
    p.add_argument('--complete',required=True,type=Path)
    p.add_argument('--cpu-sha256',required=True);p.add_argument('--native-sha256',required=True)
    p.add_argument('--output',type=Path);p.add_argument('--no-stage335-baseline',action='store_true')
    a=p.parse_args()
    try:
        result=analyze(a.cpu,a.native,a.complete,cpu_sha=a.cpu_sha256,native_sha=a.native_sha256,
                       require_stage335=not a.no_stage335_baseline)
        payload=json.dumps(result,sort_keys=True,indent=2)+'\n'
        if a.output:
            if a.output.exists() or a.output.is_symlink():raise ValueError('refuse output overwrite')
            with a.output.open('x',encoding='utf-8') as f:f.write(payload)
        else:print(payload,end='')
    except (OSError,ValueError,UnicodeError) as e:p.exit(1,'VPD_STAGE341_ORIGINAL_ALIGNMENT_INCONCLUSIVE\n')

if __name__=='__main__':main()
