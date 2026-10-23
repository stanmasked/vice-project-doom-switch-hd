#!/usr/bin/env python3
"""Conservative owner-private readiness gate for PPU raster-phase evidence.

Stage335's CPU-bus event trace cannot reveal the PPU's internal per-dot v.
The output is a *sanitized*, fail-closed inventory; the code refuses to
turn CPU-clock events into invented PPU dot/scanline or rendered scroll.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

EXPECTED_STAGE335 = {
    'ppu_status_read': 10172,
    'W2000': 844,
    'W2001': 506,
    'ppu_bus_write': 1010,
    'W2006': 6096,
}
REQUIRED = {'frame', 'sequence', 'cycle', 'event', 'ppu_toggle_before', 'ppu_toggle_after'}
MAX_BYTES = 80_000_000


def audit(path: Path, *, expected_sha256: str | None = None, require_baseline: bool = False) -> dict:
    if path.is_symlink() or not path.is_file() or not (0 < path.stat().st_size <= MAX_BYTES):
        raise ValueError('missing or oversized private source trace')
    if expected_sha256 is not None:
        if len(expected_sha256) != 64 or any(c not in '0123456789abcdef' for c in expected_sha256):
            raise ValueError('invalid expected SHA-256')
        with path.open('rb') as origin:
            sha = hashlib.file_digest(origin, 'sha256').hexdigest()
        if sha != expected_sha256:
            raise ValueError('source trace SHA-256 does not match private manifest')
    counts = Counter()
    frames = set()
    prev = None
    with path.open('r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh, delimiter='\t')
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)) or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError('unsupported or malformed private source trace schema')
        # This tool intentionally supports ONLY the original Stage335 CPU trace.
        # A future PPU core witness gets a separate format, verifier, and checksum.
        if 'scanline' in reader.fieldnames or 'ppu_dot' in reader.fieldnames or 'actual_v' in reader.fieldnames:
            raise ValueError('dot witness requires separate authenticated verifier')
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError('truncated original source row')
            f, seq, cycle = (int(row[k]) for k in ('frame','sequence','cycle'))
            if not 380 <= f <= 640 or seq <= 0 or cycle < 0:
                raise ValueError('row outside original source capture window')
            if prev is not None and (f < prev[0] or seq <= prev[1] or cycle < prev[2]):
                raise ValueError('original event order is not monotonic')
            prev = (f,seq,cycle)
            frames.add(f)
            counts[row['event']] += 1
    if frames != set(range(380, 641)):
        raise ValueError('Stage335 source frame coverage incomplete')
    if require_baseline:
        if sum(counts.values()) != 21398 or any(counts[k] != n for k,n in EXPECTED_STAGE335.items()):
            raise ValueError('original source baseline differs from sealed Stage335')
    return {
        'format': 'vpd_stage338_ppu_dot_witness_readiness_v1',
        'source_window_frames': len(frames),
        'source_cpu_event_rows': sum(counts.values()),
        'stage335_cpu_bus_baseline_matches': (sum(counts.values()) == 21398 and all(counts[k] == n for k,n in EXPECTED_STAGE335.items())),
        'source_has_cpu_cycles': True,
        'source_has_ppu_scanline_dot': False,
        'source_has_internal_v_witness': False,
        'raster_model_independently_unit_tested': True,
        'raster_witness_authenticated': False,
        'effective_raster_scroll_proven': False,
        'next_required_witness': 'independently observed PPU scanline/dot and internal v (or renderer-matched pixel evidence)',
        'private_register_values_disclosed': False,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--source-sha256',required=True)
    parser.add_argument('--require-stage335-baseline',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        summary=audit(args.input,expected_sha256=args.source_sha256,require_baseline=args.require_stage335_baseline)
        data=json.dumps(summary,indent=2,sort_keys=True)+'\n'
        if args.output:
            if args.output.exists() or args.output.is_symlink():
                raise ValueError('refusing existing or linked output')
            with args.output.open('x',encoding='utf-8') as out:out.write(data)
        else: print(data,end='')
    except (OSError,ValueError,UnicodeError):
        parser.exit(1,'VPD_STAGE338_RASTER_WITNESS_NOT_CONFIRMED\n')

if __name__=='__main__':main()
