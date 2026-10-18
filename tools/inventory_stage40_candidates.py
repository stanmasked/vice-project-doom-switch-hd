#!/usr/bin/env python3
"""Stage 40: evidence inventory of RAM writes near independently annotated video anchors.

Results are candidate observations only; no variable is assigned a camera or loader role.
"""
import argparse
import collections
import json
from pathlib import Path

from align_dispatch_video import correlate

def inventory(trace, meta, anchors, radius=1):
    aligned = correlate(trace, meta, anchors, radius)
    candidates = collections.defaultdict(lambda: {
        'writes': 0, 'anchor_labels': set(), 'values': set(), 'frames': set()
    })
    transitions = []
    for anchor in aligned['anchors']:
        if not anchor['trace_frame_within_recorded_span']:
            continue
        for event in anchor['timeline']:
            if event['kind'] == 'RAM_WRITE':
                address = event['cpu_address']
                entry = candidates[address]
                entry['writes'] += 1
                entry['anchor_labels'].add(anchor['label'])
                entry['values'].add(event['value'])
                entry['frames'].add(event['trace_frame'])
            elif event['kind'] in ('MMC3_SELECT', 'MMC3_DATA'):
                transitions.append({
                    'anchor': anchor['label'], 'frame': event['trace_frame'],
                    'kind': event['kind'], 'value': event['value'],
                    'r6': event['r6'], 'r7': event['r7'],
                    'mode': event['mmc3_mode'], 'sequence': event['sequence']
                })
    return {
        'schema': 1, 'classification': 'candidate RAM write and MMC3-event inventory, NOT game semantics',
        'rom_md5': aligned['rom_md5'], 'trace_recorded_frame_span': aligned['trace_recorded_frame_span'],
        'anchor_count': len(aligned['anchors']),
        'outside_capture_anchors': [a['label'] for a in aligned['anchors']
                                    if not a['trace_frame_within_recorded_span']],
        'ram_write_candidates': [
            {'address': addr, 'write_events_in_windows': c['writes'],
             'anchor_labels': sorted(c['anchor_labels']),
             'observed_write_values': sorted(c['values']),
             'trace_frames': sorted(c['frames'])}
            for addr, c in sorted(candidates.items())
        ],
        'mapper_events_in_windows': transitions,
        'limitations': [
            'Overlapping video windows can count one RAM write more than once',
            'Tracked RAM is limited to existing stage38 hooks; camera RAM may be elsewhere',
            'RAM_WRITE callback values are write arguments, but sampled RAM can be pre-write',
            'Anchor labels are user assertions; there is no automatic proof of first level',
            'Co-occurrence alone is not evidence of camera scrolling, stage loading or causality'
        ]
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace', type=Path)
    p.add_argument('anchors', type=Path)
    p.add_argument('--meta', type=Path)
    p.add_argument('--radius', type=int, default=1)
    p.add_argument('--out', type=Path, default=Path('private/first_level/stage40_candidates.json'))
    args = p.parse_args()
    data = inventory(args.trace, args.meta or args.trace.with_suffix('.meta.txt'),
                     args.anchors, args.radius)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf8')
    print(json.dumps({'candidates':len(data['ram_write_candidates']),
                      'mapper_events':len(data['mapper_events_in_windows']),
                      'out':str(args.out)},indent=2))

if __name__=='__main__':
    main()
