#!/usr/bin/env python3
"""Stage50 strict joint-event replay; preceding PC is not proven read origin."""
import argparse
import collections
import csv
import json
import re
from pathlib import Path
from analyze_dispatch_execution import mapping, hx, numeric

FIELDS=['frame','seq','kind','address','value','physical_bank']
PCS={0xE479,0xE4E6,0xE4F3,0x835B,0xC906}
KINDS={'EXEC','READ','SELECT','DATA'}
REQUIRED={'format':'vice_stage49_joint_v1',
          'exec_context':'selected_pc_hooks_only','read_causality':'not_proven',
          'read_value_provenance':'address_only_fceux_zero_sentinel'}

def validate(trace,meta):
    props={}
    for line in Path(meta).read_text(encoding='utf8').splitlines():
        if '=' not in line:raise ValueError('Malformed metadata')
        k,v=line.split('=',1)
        if k in props:raise ValueError('Duplicate metadata')
        props[k]=v
    if any(props.get(k)!=v for k,v in REQUIRED.items()):
        raise ValueError('Invalid capture provenance')
    for k in ('events_recorded','events_dropped'):
        if not re.fullmatch(r'[0-9]+',props.get(k,'')):
            raise ValueError('Invalid event count')
    if props.get('complete') not in ('yes','no') or (
        props['complete']=='yes') != (int(props['events_dropped'])==0):
        raise ValueError('Contradictory completeness')
    if props['complete']!='yes':
        raise ValueError('Incomplete joint trace')
    selected=r6=r7=None
    previous_frame=0
    counts=collections.Counter()
    unknown=0
    observed=0
    with Path(trace).open(newline='',encoding='utf8') as stream:
        reader=csv.DictReader(stream,delimiter='\t')
        if reader.fieldnames!=FIELDS:raise ValueError('Unexpected trace columns')
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError('Malformed trace row')
            observed+=1
            frame=numeric(row['frame'],'frame',0,10**9)
            if frame<previous_frame:raise ValueError('Frame order')
            previous_frame=frame
            if numeric(row['seq'],'sequence',1,10**9)!=observed:
                raise ValueError('Event sequence')
            kind=row['kind']
            if kind not in KINDS:raise ValueError('Unknown kind')
            addr=hx(row['address'],'address',4)
            v=None if row['value']=='unknown' else hx(row['value'],'value',2)
            if kind=='EXEC':
                if addr not in PCS or v is not None:raise ValueError('Invalid EXEC')
            elif kind=='READ':
                if addr<0x8000 or v is not None:raise ValueError('Invalid READ value provenance')
            else:
                if addr!=(0x8000 if kind=='SELECT' else 0x8001) or v is None:
                    raise ValueError('Invalid mapper write')
            if kind=='SELECT':selected=v
            elif kind=='DATA' and selected is not None:
                if selected%8==6:r6=v
                if selected%8==7:r7=v
            bank,_=mapping(addr,selected,r6,r7)
            expected='unknown' if bank is None else str(bank)
            if row['physical_bank']!=expected:
                raise ValueError('Physical bank mismatch')
            if kind=='READ' and bank is None:unknown+=1
            counts[kind]+=1
    if observed!=int(props['events_recorded']):
        raise ValueError('Event count mismatch')
    return {'schema':1,'events':observed,'counts':dict(counts),
            'unknown_bank_reads':unknown,'complete':True,
            'read_values_proven':False,
            'cpu_read_causality_proven':False,
            'classification':'ordered callbacks with bank replay, not instruction causality'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace',type=Path)
    p.add_argument('--meta',type=Path)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    result=validate(a.trace,a.meta or a.trace.with_suffix('.meta.txt'))
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
