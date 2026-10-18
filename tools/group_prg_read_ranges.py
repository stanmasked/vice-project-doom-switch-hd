#!/usr/bin/env python3
"""Stage47: group adjacent mapped PRG reads without calling them level data."""
import argparse
import collections
import json
import csv
from pathlib import Path
from audit_prg_read_mapping import audit_verified

def runs(trace, meta, min_run=2):
    if not 1 <= min_run <= 10000:
        raise ValueError('min_run must be between 1 and 10000')
    checked=audit_verified(trace,meta)
    spans=[]
    current=None
    unresolved=0
    # Rebuild only chronological event positions. A mapper write is a barrier
    # even if the next READ eventually maps back to the same bank.
    with Path(trace).open(newline='',encoding='utf8') as stream:
        events=list(csv.DictReader(stream,delimiter='\t'))
    read_iter=iter(checked['reads'])
    for event in events:
        if event['kind']!='READ':
            if current is not None:
                spans.append(current)
                current=None
            continue
        item=next(read_iter)
        offset=item['physical_prg_offset']
        if offset is None:
            unresolved+=1
            if current is not None:
                spans.append(current)
                current=None
            continue
        if current is not None and item['bank']==current['bank'] and item['frame']==current['last_frame'] and offset==current['end_offset']+1:
            current['end_offset']=offset
            current['read_events']+=1
            continue
        if current is not None:
            spans.append(current)
        current={'bank':item['bank'],'start_offset':offset,'end_offset':offset,
                 'first_frame':item['frame'],'last_frame':item['frame'],
                 'read_events':1}
    if current is not None: spans.append(current)
    selected=[s for s in spans if s['read_events']>=min_run]
    repeats=collections.Counter((s['bank'],s['start_offset'],s['end_offset']) for s in selected)
    return {
        'schema':1,'classification':'adjacent mapped CPU-read runs; data meaning unverified',
        'capture_metadata_verified':checked['capture_metadata_verified'],
        'event_counts':checked['event_counts'],'unresolved_reads':unresolved,
        'read_values_proven':False,
        'candidate_runs':[dict(s, occurrences_of_same_range=repeats[(s['bank'],s['start_offset'],s['end_offset'])])
                          for s in selected],
        'discarded_short_runs':len(spans)-len(selected),
        'limitations':[
            'CPU-bus reads may be instruction fetches, not data accesses',
            'Only successive READ events are grouped; this is not a decoded map',
            'An identical observed range is not evidence of level identity',
            'Read callback semantics and first-level footage remain unverified'
        ]
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace',type=Path)
    p.add_argument('--meta',type=Path)
    p.add_argument('--min-run',type=int,default=2)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    result=runs(a.trace,a.meta or a.trace.with_suffix('.meta.txt'),a.min_run)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
