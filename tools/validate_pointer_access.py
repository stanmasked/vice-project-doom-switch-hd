#!/usr/bin/env python3
"""Validate private stage41 pointer-byte callback logs; never infer PRG ROM reads."""
import argparse
import csv
import json
import re
from pathlib import Path

FIELDS=['frame','seq','kind','address','value','aa','ab','a8','a9']
ADDRESSES={'00AA','00AB','00A8','00A9'}

def validate(trace,meta):
    props={}
    for line in Path(meta).read_text(encoding='utf8').splitlines():
        if '=' not in line: raise ValueError('Invalid metadata')
        key,val=line.split('=',1)
        if key in props: raise ValueError('Duplicate metadata')
        props[key]=val
    required={'format':'vice_stage41_pointer_access_v1',
              'execution_pc':'not_instrumented',
              'meaning':'pointer_byte_access_not_dereference'}
    if any(props.get(k)!=v for k,v in required.items()):
        raise ValueError('Untrusted provenance')
    if not re.fullmatch('[0-9a-fA-F]{32}',props.get('rom_md5','')):
        raise ValueError('Invalid ROM identifier')
    for key in ('events_recorded','events_dropped'):
        if not re.fullmatch('[0-9]+',props.get(key,'')):
            raise ValueError('Invalid event counts')
    total=int(props['events_recorded'])
    dropped=int(props['events_dropped'])
    if props.get('complete')!=('yes' if dropped==0 else 'no'):
        raise ValueError('Inconsistent completeness')
    observed=0
    previous_frame=None
    counts={'READ':0,'WRITE':0}
    with Path(trace).open(encoding='utf8',newline='') as stream:
        reader=csv.DictReader(stream,delimiter='\t')
        if reader.fieldnames!=FIELDS: raise ValueError('Invalid event schema')
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError('Malformed event row')
            if not re.fullmatch('[0-9]+',row['frame']):
                raise ValueError('Invalid frame')
            frame=int(row['frame'])
            if previous_frame is not None and frame<previous_frame:
                raise ValueError('Frame order')
            previous_frame=frame
            observed+=1
            if row['seq']!=str(observed): raise ValueError('Event sequence')
            if row['kind'] not in counts or row['address'] not in ADDRESSES:
                raise ValueError('Unexpected RAM access')
            if any(not re.fullmatch('[0-9A-F]{2}',row[key]) for key in FIELDS[4:]):
                raise ValueError('Invalid byte')
            counts[row['kind']]+=1
    if observed!=total:raise ValueError('Recorded event count mismatch')
    return {'schema':1,'rom_md5':props['rom_md5'].lower(),
            'events_recorded':observed,'events_dropped':dropped,
            'complete':dropped==0,'ram_byte_reads':counts['READ'],
            'ram_byte_writes':counts['WRITE'],
            'prg_rom_reads_observed':False,
            'effective_addresses_observed':False,
            'cpu_instruction_pc_observed':False,
            'classification':'RAM byte callback access only, NOT ROM dereference'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace',type=Path)
    p.add_argument('--meta',type=Path)
    p.add_argument('--out',type=Path)
    args=p.parse_args()
    result=validate(args.trace,args.meta or args.trace.with_suffix('.meta.txt'))
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
