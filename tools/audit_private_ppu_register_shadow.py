#!/usr/bin/env python3
"""Replay CPU-visible PPU scroll/address register writes without inferring raster v.

Stage 337: the owner-local TSV contains original game byte values; this tool
emits ONLY aggregates. The NES PPU updates internal v through rendering
steps, not just CPU writes. This program deliberately never reconstructs or
claims scanline-effective scroll, VRAM fetch v, camera motion, or collision.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

FIELDS = ('frame', 'sequence', 'cycle', 'event', 'value',
          'ppu_toggle_before', 'ppu_toggle_after', 'ppu_ordinal')
REAL_EVENTS = ('ppu_status_read', 'W2000', 'W2001', 'W2006', 'ppu_bus_write')
MAX_BYTES = 80_000_000


def _byte(s: str) -> int:
    if len(s) != 2 or any(c not in '0123456789abcdefABCDEF' for c in s):
        raise ValueError('invalid private PPU register byte')
    return int(s, 16)


def shadow_audit(path: Path, start: int = 380, end: int = 640) -> dict:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_BYTES:
        raise ValueError('private trace missing, symlinked, empty, or oversized')
    if not 0 <= start <= end <= 100_000:
        raise ValueError('invalid window')
    totals = Counter()
    frames = defaultdict(Counter)
    pairs = defaultdict(list)
    # t is a register shadow, not the actual rendered v after PPU dot-level updates.
    t, v_from_cpu_2006, fine_x, w = 0, 0, 0, 0
    previous_order = None
    status_observed = False
    ppu2001_mask = None
    with path.open('r', encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError('duplicate or absent trace headers')
        if not set(FIELDS).issubset(reader.fieldnames):
            raise ValueError('private event trace missing mandatory fields')
        n_rows = 0
        seen_frames = set()
        for row in reader:
            if None in row or any(item is None for item in row.values()):
                raise ValueError('truncated TSV row')
            try:
                frame, seq, cycle = int(row['frame']), int(row['sequence']), int(row['cycle'])
            except ValueError as exc:
                raise ValueError('invalid frame/sequence/cycle') from exc
            if not start <= frame <= end or not 0 < seq or not 0 <= cycle:
                raise ValueError('private row outside declared source frame window')
            key = (frame, seq, cycle)
            if previous_order is not None and (seq <= previous_order[1] or frame < previous_order[0] or cycle < previous_order[2]):
                raise ValueError('non-monotonic event order')
            previous_order = key
            n_rows += 1
            seen_frames.add(frame)
            kind = row['event']
            if kind not in REAL_EVENTS:
                continue
            val = _byte(row['value'])
            before = row['ppu_toggle_before']
            after = row['ppu_toggle_after']
            if before not in ('0', '1') or after not in ('0', '1'):
                raise ValueError('missing observed FCEUX write-toggle witness')
            if int(before) != w:
                raise ValueError('captured write-toggle phase disagrees with CPU register replay')
            totals[kind] += 1
            frames[frame][kind] += 1
            previous_w = w
            if kind == 'ppu_status_read':
                w = 0
                status_observed = True
            elif kind == 'W2000':
                # PPUCTRL bits 0-1 replace t[10:11]; w stays unchanged.
                t = (t & 0x73FF) | ((val & 0x03) << 10)
            elif kind == 'W2001':
                ppu2001_mask = val
            elif kind == 'W2006':
                if w == 0:
                    t = (t & 0x00FF) | ((val & 0x3F) << 8)
                    w = 1
                else:
                    t = (t & 0x7F00) | val
                    v_from_cpu_2006 = t
                    w = 0
                    totals['cpu_2006_v_assignment'] += 1
            elif kind == 'ppu_bus_write':
                if w == 0:
                    t = (t & 0x7FE0) | (val >> 3)
                    fine_x = val & 7
                    w = 1
                    totals['first_2005_write'] += 1
                else:
                    t = (t & 0x0C1F) | ((val & 0xF8) << 2) | ((val & 7) << 12)
                    w = 0
                    totals['second_2005_write'] += 1
                ordinal = row['ppu_ordinal']
                if not ordinal.isdecimal() or int(ordinal) < 1:
                    raise ValueError('PPUSCROLL bus write ordinal missing')
                pairs[frame].append((int(ordinal), previous_w, w))
            if int(after) != w:
                raise ValueError('captured write-toggle after-state differs from CPU register replay')
    if not status_observed or seen_frames != set(range(start, end + 1)):
        raise ValueError('missing PPUSTATUS witness or missing source frames')
    if totals['ppu_bus_write'] != sum(frames[f]['ppu_bus_write'] for f in seen_frames):
        raise ValueError('PPUSCROLL counting inconsistency')
    for frame, pair_list in pairs.items():
        ordinals = [p[0] for p in pair_list]
        if ordinals != list(range(1, len(ordinals) + 1)):
            raise ValueError('frame-local PPUSCROLL ordinal discontinuity')
    active_frames = sum(bool(frames[f]['ppu_bus_write']) for f in seen_frames)
    frame2005_cardinality = Counter(frames[f]['ppu_bus_write'] for f in sorted(seen_frames))
    # IMPORTANT: The actual PPU v register is modified by rendering-dots,
    # horizontal/vertical scroll reloads and address increments that are not
    # present in this CPU event stream. v_from_cpu_2006 is not rendered v.
    return {
        'format': 'vpd_stage337_private_ppu_cpu_write_shadow_aggregate_v1',
        'frame_window': [start, end],
        'source_frames': len(seen_frames),
        'cpu_event_rows_processed': n_rows,
        'ppu_bus_events': {
            'PPUSTATUS_read_witnesses': totals['ppu_status_read'],
            'PPUCTRL_2000_writes': totals['W2000'],
            'PPUMASK_2001_writes': totals['W2001'],
            'PPUSCROLL_2005_writes': totals['ppu_bus_write'],
            'PPUADDR_2006_writes': totals['W2006'],
            'PPUADDR_2006_second_half_cpu_v_assignments': totals['cpu_2006_v_assignment'],
        },
        'scroll_input_phase_counts': {
            'first_2005': totals['first_2005_write'],
            'second_2005': totals['second_2005_write'],
            'frames_with_2005': active_frames,
            'per_frame_2005_count_distribution': {str(k):v for k,v in sorted(frame2005_cardinality.items())},
        },
        'toggle_mismatches': 0,
        'observed_ppu_status_resets': totals['ppu_status_read'],
        'cpu_register_shadow_computed': True,
        'cpu_v_assignment_from_2006_recorded': True,
        'actual_ppu_v_during_rendering_known': False,
        'scanline_and_ppu_dot_timing_captured': False,
        'effective_raster_scroll_proven': False,
        'road_geometry_proven': False,
        'camera_speed_proven': False,
        'private_raw_values_disclosed': False,
    }


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--start',type=int,default=380)
    parser.add_argument('--end',type=int,default=640)
    parser.add_argument('--require-stage335-baseline',action='store_true')
    args=parser.parse_args()
    try:
        result=shadow_audit(args.input,args.start,args.end)
        if args.require_stage335_baseline:
            required={'PPUSTATUS_read_witnesses':10172,'PPUCTRL_2000_writes':844,'PPUMASK_2001_writes':506,'PPUSCROLL_2005_writes':1010,'PPUADDR_2006_writes':6096,'PPUADDR_2006_second_half_cpu_v_assignments':3048}
            if (result['frame_window'] != [380,640] or any(result['ppu_bus_events'][k]!=v for k,v in required.items()) or result['scroll_input_phase_counts']['frames_with_2005'] != 253 or result['scroll_input_phase_counts']['first_2005'] != 505 or result['scroll_input_phase_counts']['second_2005'] != 505):
                raise ValueError('source trace does not reproduce Stage 335 baseline')
        payload=json.dumps(result,indent=2,sort_keys=True)+'\n'
        if args.output:
            if args.output.exists() or args.output.is_symlink():
                raise ValueError('refusing existing or linked report path')
            with args.output.open('x',encoding='utf-8') as out:out.write(payload)
        else:print(payload)
    except (OSError,UnicodeError,ValueError):
        parser.exit(1,'VPD_PRIVATE_STAGE337_INCONCLUSIVE input/PPU latch validation failed\n')

if __name__=='__main__':main()
