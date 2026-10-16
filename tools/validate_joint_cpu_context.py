#!/usr/bin/env python3
"""Strict stage53 joint context log replay. No instruction/read causality inferred."""
import argparse
import collections
import csv
import json
import re
from pathlib import Path
from analyze_dispatch_execution import mapping, hx, numeric

FIELDS=['frame','seq','kind','address','value','bank','a','x','y','s','p']
PCS={0xE479,0xE4E6,0xE4F3,0x835B,0xC906}
PROVENANCE={
    'format':'vice_stage53_joint_context_v1',
    'rom_header_profile':'ines_mapper4_prg128k',
    'initial_mmc3_mode':'unknown',
    'register_provenance':'callback_time_optional_samples',
    'register_api':'memory.getregister',
    'callback_contract':'address_size_value_v1',
    'effective_address':'not_proven',
    'read_causality':'not_proven'
}

def validate(trace,meta):
    fields={}
    for line in Path(meta).read_text(encoding='utf8').splitlines():
        if '=' not in line:raise ValueError('Malformed metadata')
        k,v=line.split('=',1)
        if k in fields:raise ValueError('Duplicate metadata key')
        fields[k]=v
    if any(fields.get(k)!=v for k,v in PROVENANCE.items()):
        raise ValueError('Untrusted provenance')
    if fields.get('rom_md5_pin') not in ('matched','not_supplied'):
        raise ValueError('Invalid ROM pin metadata')
    for key in ('events_recorded','events_dropped'):
        if not re.fullmatch(r'[0-9]+',fields.get(key,'')):
            raise ValueError('Invalid event count')
    errors_field=fields.get('callback_errors','')
    if not re.fullmatch(r'[0-9]+',errors_field):
        raise ValueError('Missing or invalid callback error count')
    callback_errors=int(errors_field)
    dropped=int(fields['events_dropped'])
    if fields.get('complete')!=('yes' if dropped==0 and callback_errors==0 else 'no'):
        raise ValueError('Inconsistent completeness flag')
    if dropped or callback_errors:raise ValueError('Incomplete capture or invalid FCEUX callbacks')
    selected=r6=r7=None
    count=0
    prev_frame=0
    kinds=collections.Counter()
    unknown_registers=collections.Counter()
    unknown_banks=0
    with Path(trace).open(newline='',encoding='utf8') as stream:
        reader=csv.DictReader(stream,delimiter='\t')
        if reader.fieldnames!=FIELDS:raise ValueError('Invalid TSV schema')
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError('Malformed row')
            count+=1
            frame=numeric(row['frame'],'frame',0,10**9)
            if frame<prev_frame:raise ValueError('Nonmonotonic frames')
            prev_frame=frame
            if numeric(row['seq'],'sequence',1,10**9)!=count:
                raise ValueError('Event order mismatch')
            kind=row['kind']
            if kind not in ('EXEC','READ','SELECT','DATA'):
                raise ValueError('Invalid event kind')
            addr=hx(row['address'],'CPU address',4)
            value=None if row['value']=='unknown' else hx(row['value'],'value',2)
            if kind=='EXEC':
                if addr not in PCS or value is not None:raise ValueError('Invalid EXEC')
            elif kind=='READ':
                if addr<0x8000 or value is None:raise ValueError('Invalid READ')
            elif addr!=(0x8000 if kind=='SELECT' else 0x8001) or value is None:
                raise ValueError('Invalid MMC3 write')
            if kind=='SELECT':selected=value
            if kind=='DATA' and selected is not None:
                if selected%8==6:r6=value
                if selected%8==7:r7=value
            bank,_=mapping(addr,selected,r6,r7)
            if row['bank']!=('unknown' if bank is None else str(bank)):
                raise ValueError('MMC3 mapping mismatch')
            if kind=='READ' and bank is None:unknown_banks+=1
            for reg in ('a','x','y','s','p'):
                if row[reg]=='unknown':unknown_registers[reg]+=1
                else:hx(row[reg],reg,2)
            kinds[kind]+=1
    if count!=int(fields['events_recorded']):
        raise ValueError('Metadata event count mismatch')
    return {'schema':1,'complete':True,'events':count,
            'event_counts':dict(sorted(kinds.items())),
            'unknown_register_samples':dict(sorted(unknown_registers.items())),
            'unknown_bank_reads':unknown_banks,
            'effective_address_proven':False,'read_causality_proven':False,
            'classification':'validated callback-order and register samples only'}

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
