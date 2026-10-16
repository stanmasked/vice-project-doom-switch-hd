#!/usr/bin/env python3
"""Stage 39: correlate manually verified gameplay video anchors with FCEUX events.

Does not infer camera or level data from event addresses. Private inputs stay local.
"""
import argparse
import collections
import csv
import json
from pathlib import Path

from analyze_dispatch_execution import FIELDS, analyze, hx, numeric

ANCHORS = ['video_frame', 'trace_frame', 'label']
SAMPLES = ('ram_07', 'ram_90', 'ram_91', 'ram_92', 'ram_aa', 'ram_ab', 'ram_a8', 'ram_a9')
INTERESTING = {'EXEC', 'RAM_WRITE', 'MMC3_SELECT', 'MMC3_DATA'}

def correlate(trace_path, meta_path, anchors_path, radius=1):
    if not 0 <= radius <= 120:
        raise ValueError('Frame radius must be between 0 and 120')
    audit = analyze(trace_path, meta_path)
    if not audit['complete']:
        raise ValueError('Incomplete trace is not video-alignment evidence')
    with Path(anchors_path).open(newline='', encoding='utf8') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ANCHORS:
            raise ValueError('Expected video_frame,trace_frame,label columns')
        anchors = []
        for row in reader:
            if None in row or any(x is None for x in row.values()):
                raise ValueError('Malformed anchor row')
            v = numeric(row['video_frame'], 'video frame', 0, 10**9)
            t = numeric(row['trace_frame'], 'trace frame', 0, 10**9)
            label = row['label'].strip()
            if not label or len(label) > 120:
                raise ValueError('Anchor label must contain 1..120 characters')
            if anchors and (v <= anchors[-1]['video_frame'] or t <= anchors[-1]['trace_frame']):
                raise ValueError('Video and trace anchors must both increase strictly')
            anchors.append({'video_frame': v, 'trace_frame': t, 'label': label})
    if not anchors:
        raise ValueError('At least one manually verified anchor required')
    events = []
    trace_first_frame = None
    trace_last_frame = None
    with Path(trace_path).open(newline='', encoding='utf8') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        if reader.fieldnames != FIELDS:
            raise ValueError('Unexpected trace fields')
        for row in reader:
            frame = int(row['frame'])
            if trace_first_frame is None:
                trace_first_frame = frame
            trace_last_frame = frame
            if not any(abs(frame - a['trace_frame']) <= radius for a in anchors):
                continue
            addr = hx(row['cpu_address'], 'address', 4)
            if row['kind'] not in INTERESTING:
                raise ValueError('Unexpected event type')
            events.append({
                'trace_frame': frame, 'sequence': int(row['seq']),
                'kind': row['kind'], 'cpu_address': '$%04X' % addr,
                'value': row['value'],
                'physical_prg_bank': None if row['mapped_bank']=='unknown' else int(row['mapped_bank']),
                'mapping_status': row['mapping_status'],
                'mmc3_mode': row['mmc3_mode'],
                'r6': row['r6'], 'r7': row['r7'],
                'sampled_ram': {key: row[key] for key in SAMPLES},
                'sample_semantics': 'write callbacks may contain pre-write RAM snapshots'
            })
    results = []
    for a in anchors:
        nearby = [e for e in events if abs(e['trace_frame'] - a['trace_frame']) <= radius]
        dispatch = [e for e in nearby if e['kind']=='EXEC']
        in_range = (trace_first_frame is not None and
                    trace_first_frame <= a['trace_frame'] <= trace_last_frame)
        results.append({**a, 'radius_frames': radius, 'events': len(nearby),
                        'trace_frame_within_recorded_span': in_range,
                        'anchor_has_instrumented_events': bool(nearby),
                        'dispatcher_executions': collections.Counter(e['cpu_address'] for e in dispatch),
                        'unknown_bank_executions': sum(e['kind']=='EXEC' and e['physical_prg_bank'] is None and
                                                      int(e['cpu_address'][1:],16)>=0x8000 for e in nearby),
                        'timeline': nearby})
    return {
        'schema': 1, 'source': 'user-verified video anchors + FCEUX stage38 execution callbacks',
        'rom_md5': audit['rom_md5'], 'video_identity': 'not independently verified',
        'first_level_identity': 'not verified by alignment alone',
        'trace_recorded_frame_span': [trace_first_frame, trace_last_frame],
        'anchors': results,
        'limitations': [
            'Video-frame to emulator-frame correspondence is manually asserted',
            'Only instrumented PCs and RAM/mapper writes are observable',
            'RAM samples may predate the writes whose callbacks recorded them',
            'An execution PC does not identify camera, collision or level data semantics',
            'Frames without instrumented events are not proof of inactivity',
            'An anchor outside the recorded frame span cannot be corroborated',
            'No interpolation or timing extrapolation between anchors is performed'
        ]
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace', type=Path)
    p.add_argument('anchors', type=Path, help='CSV with video_frame,trace_frame,label')
    p.add_argument('--meta', type=Path)
    p.add_argument('--radius', type=int, default=1)
    p.add_argument('--out', type=Path, default=Path('private/first_level/stage39_alignment.json'))
    args = p.parse_args()
    data = correlate(args.trace, args.meta or args.trace.with_suffix('.meta.txt'),
                     args.anchors, args.radius)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf8')
    print(json.dumps({'anchors':len(data['anchors']),
                      'event_windows':[x['events'] for x in data['anchors']],
                      'out':str(args.out)},indent=2))

if __name__=='__main__':
    main()
