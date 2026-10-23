#!/usr/bin/env python3
"""Validate an opt-in classic FCEUX source trace, publishing ONLY aggregates.

Classic RefreshAddr and legacy renderer-pixel positions are not independently
observed hardware PPU-dot phase or movie frame numbers. Never conflate them.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

FIELDS = ('core_frame_ordinal','cpu_timestamp','event','legacy_scanline',
          'renderer_pixel_not_dot','refresh_addr','temp_addr',
          'write_toggle','fine_x','ppu_mask')
EVENTS = {'core_frame_start','legacy_line_start','legacy_line_256_cpu_slice',
          'legacy_line_end','legacy_horizontal_reload','legacy_vertical_increment',
          'cpu_second_2006'}
MAX_SIZE=80_000_000


def audit(path: Path, *, first: int=380,last: int=640, expected_sha256: str|None=None) -> dict:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_SIZE:
        raise ValueError('private trace absent, symlinked, or outside size limit')
    if not 0<=first<=last<=100_000 or last-first>1000:
        raise ValueError('core-frame capture window invalid')
    if expected_sha256 is not None:
        if len(expected_sha256)!=64 or any(c not in '0123456789abcdef' for c in expected_sha256):
            raise ValueError('invalid expected SHA-256')
        with path.open('rb') as f:
            if hashlib.file_digest(f,'sha256').hexdigest()!=expected_sha256:
                raise ValueError('private trace checksum mismatch')
    counts=Counter()
    frame_counts=Counter()
    before=None
    rows=0
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        rd=csv.DictReader(f,delimiter='\t')
        if rd.fieldnames!=list(FIELDS):
            raise ValueError('unrecognized Stage340 private trace schema')
        for row in rd:
            if None in row or any(v is None for v in row.values()):
                raise ValueError('truncated or unexpected Stage340 row')
            try:
                frame=int(row['core_frame_ordinal']);tick=int(row['cpu_timestamp'])
                sl=int(row['legacy_scanline']);pixel=int(row['renderer_pixel_not_dot'])
                ra=int(row['refresh_addr'],16);ta=int(row['temp_addr'],16)
                w=int(row['write_toggle']);x=int(row['fine_x']);mask=int(row['ppu_mask'])
            except (ValueError,TypeError) as exc:
                raise ValueError('invalid Stage340 source register field') from exc
            if not first<=frame<=last or not 0<=tick<=0xffffffff or not -1<=sl<=300 or not -1<=pixel<=256:
                raise ValueError('source trace event outside declared scope')
            if not 0<=ra<0x8000 or not 0<=ta<0x8000 or w not in (0,1) or not 0<=x<=7 or not 0<=mask<=255:
                raise ValueError('invalid legacy PPU source value')
            event=row['event']
            if event not in EVENTS:
                raise ValueError('unknown/truncated legacy PPU event')
            if before is not None and (frame<before[0] or (frame==before[0] and tick<before[1])):
                raise ValueError('nonmonotonic original core frame/timestamp')
            before=(frame,tick)
            counts[event]+=1;rows+=1
            if event=='core_frame_start':
                frame_counts[frame]+=1
    if not rows or set(frame_counts)!=set(range(first,last+1)) or any(c!=1 for c in frame_counts.values()):
        raise ValueError('incomplete/duplicate classic PPU frame markers')
    required=('legacy_line_start','legacy_line_256_cpu_slice','legacy_horizontal_reload','legacy_vertical_increment','legacy_line_end')
    if any(counts[k]==0 for k in required):
        raise ValueError('missing classic PPU transition evidence')
    return {
        'format':'vpd_stage340_private_legacy_ppu_core_aggregate_v1',
        'core_frame_window':[first,last],
        'core_frames_observed':len(frame_counts),
        'private_source_rows':rows,
        'event_counts':{k:counts[k] for k in sorted(EVENTS)},
        'classic_core_refreshaddr_transitions_observed':True,
        'renderer_pixel_position_is_ppu_dot':False,
        'movie_frame_alignment_verified':False,
        'exact_hardware_ppu_dot_observed':False,
        'raster_effective_scroll_proven':False,
        'road_geometry_proven':False,
        'private_values_disclosed':False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--first-core-frame',type=int,default=380)
    p.add_argument('--last-core-frame',type=int,default=640)
    p.add_argument('--sha256',required=True)
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    try:
        data=audit(args.input,first=args.first_core_frame,last=args.last_core_frame,expected_sha256=args.sha256)
        payload=json.dumps(data,indent=2,sort_keys=True)+'\n'
        if args.output:
            if args.output.exists() or args.output.is_symlink():
                raise ValueError('refuse overwrite of private aggregate')
            args.output.write_text(payload,encoding='utf-8')
        else:
            print(payload,end='')
    except (OSError,ValueError,UnicodeError):
        p.exit(1,'VPD_STAGE340_LEGACY_CORE_WITNESS_INCONCLUSIVE\n')

if __name__=='__main__':main()
