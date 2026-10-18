#!/usr/bin/env python3
"""Stage51: candidate EXEC-to-READ adjacency, never instruction causality."""
import argparse
import csv
import json
from pathlib import Path
from validate_joint_trace import FIELDS, validate

def neighbors(trace,meta,max_gap=3):
    if not isinstance(max_gap,int) or not 1<=max_gap<=1000:
        raise ValueError('max_gap must be 1..1000')
    checked=validate(trace,meta)
    previous=None
    pairs=[]
    blocked={'frame_change':0,'mapper_intervened':0,'gap_exceeded':0,'no_exec':0}
    with Path(trace).open(newline='',encoding='utf8') as f:
        reader=csv.DictReader(f,delimiter='\t')
        for row in reader:
            kind=row['kind']
            if kind=='EXEC':
                previous={'seq':int(row['seq']),'frame':int(row['frame']),
                          'address':row['address'],'bank':row['physical_bank'],
                          'mapper_intervened':False}
            elif kind in ('SELECT','DATA'):
                if previous:previous['mapper_intervened']=True
            elif kind=='READ':
                seq=int(row['seq']);frame=int(row['frame'])
                if previous is None:blocked['no_exec']+=1
                elif previous['frame']!=frame:blocked['frame_change']+=1
                elif previous['mapper_intervened']:blocked['mapper_intervened']+=1
                elif seq-previous['seq']>max_gap:blocked['gap_exceeded']+=1
                else:
                    pairs.append({'exec_seq':previous['seq'],
                                  'read_seq':seq,'frame':frame,
                                  'exec_pc':previous['address'],
                                  'read_cpu_address':row['address'],
                                  'exec_bank':previous['bank'],
                                  'read_bank':row['physical_bank'],
                                  'event_gap':seq-previous['seq'],
                                  'relation':'temporal_neighbor_only'})
    return {'schema':1,'complete':checked['complete'],
            'candidates':pairs,'excluded_read_counts':blocked,
            'causality_proven':False,
            'limitations':['Sparse execution hooks can skip instructions',
                           'Adjacent events do not imply an instruction issued a read',
                           'No CPU registers, opcode decoding or effective address proof']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace',type=Path)
    p.add_argument('--meta',type=Path)
    p.add_argument('--max-gap',type=int,default=3)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    result=neighbors(a.trace,a.meta or a.trace.with_suffix('.meta.txt'),a.max_gap)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
