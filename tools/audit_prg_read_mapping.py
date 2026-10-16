#!/usr/bin/env python3
"""Stage44: audit user-supplied PRG read observations against MMC3 mapper writes.

A READ is an observed CPU-bus address, not proof of stage geometry or source opcode.
No ROM bytes are stored in this tool.
"""
import argparse
import csv
import json
import re
from pathlib import Path
from analyze_dispatch_execution import mapping, numeric, hx

FIELDS=['frame','seq','kind','cpu_address','value','mapped_bank']
KINDS={'SELECT','DATA','READ'}

def audit(path):
    selected=r6=r7=None
    prior_frame=0
    counts={k:0 for k in KINDS}
    reads=[]
    with Path(path).open(newline='',encoding='utf8') as f:
        reader=csv.DictReader(f,delimiter='\t')
        if reader.fieldnames!=FIELDS:
            raise ValueError('Invalid PRG observation schema')
        for expected,row in enumerate(reader,1):
            if None in row or any(v is None for v in row.values()):
                raise ValueError('Malformed observation')
            frame=numeric(row['frame'],'frame',0,10**9)
            if frame<prior_frame: raise ValueError('Frames not monotonic')
            prior_frame=frame
            if numeric(row['seq'],'sequence',1,10**9)!=expected:
                raise ValueError('Missing or reordered observations')
            kind=row['kind']
            if kind not in KINDS: raise ValueError('Unknown event type')
            addr=hx(row['cpu_address'],'CPU address',4)
            value=None if row['value']=='unknown' else hx(row['value'],'byte',2)
            if kind=='READ' and value is not None:
                raise ValueError('Invalid READ value provenance')
            if kind!='READ' and value is None:
                raise ValueError('Missing MMC3 write value')
            if kind=='SELECT':
                if addr!=0x8000:raise ValueError('Bad MMC3 SELECT address')
                selected=value
            elif kind=='DATA':
                if addr!=0x8001:raise ValueError('Bad MMC3 DATA address')
                if selected is not None:
                    if selected%8==6:r6=value
                    if selected%8==7:r7=value
            else:
                if not 0x8000<=addr<=0xffff:
                    raise ValueError('PRG read outside cartridge CPU window')
            bank,status=mapping(addr,selected,r6,r7)
            expected_bank='unknown' if bank is None else str(bank)
            if row['mapped_bank']!=expected_bank:
                raise ValueError('Observed bank disagrees with replay')
            counts[kind]+=1
            if kind=='READ':
                reads.append({'frame':frame,'cpu_address':f'{addr:04X}',
                              'bank':bank,'mapping_status':status,
                              'physical_prg_offset':None if bank is None else
                                  bank*8192+(addr%8192)})
    return {
        'schema':1,'classification':'CPU-bus read candidates, not decoded stage data',
        'event_counts':counts,'reads':reads,'read_values_proven':False,
        'unresolved_reads':sum(v['bank'] is None for v in reads),
        'limitations':[
            'Input must originate from independently verified bus read callbacks',
            'MMC3 initial mode/R6/R7 remains unknown until observed writes',
            'A read does not identify the executing CPU instruction',
            'CPU mapping does not verify byte content or first-stage identity',
            'Read events captured in separate sessions cannot be interleaved with mapper events'
        ]
    }

def audit_verified(path, meta_path):
    """Require and cross-check same-session capture metadata."""
    props={}
    for line in Path(meta_path).read_text(encoding='utf8').splitlines():
        if not line or '=' not in line:
            raise ValueError('Malformed capture metadata')
        key,value=line.split('=',1)
        if key in props: raise ValueError('Duplicate capture metadata key')
        props[key]=value
    required={'format':'vice_stage45_prg_reads_v1',
              'initial_mmc3_mode':'unknown',
              'read_provenance':'registerread_callback_no_pc_proof',
              'read_value_provenance':'address_only_fceux_zero_sentinel'}
    if any(props.get(k)!=v for k,v in required.items()):
        raise ValueError('Invalid capture provenance')
    for name in ('events_recorded','events_dropped'):
        if not re.fullmatch(r'[0-9]+',props.get(name,'')):
            raise ValueError('Invalid capture count')
    if props.get('complete') not in ('yes','no'):
        raise ValueError('Invalid completeness value')
    dropped=int(props['events_dropped'])
    if props['complete']!=('yes' if dropped==0 else 'no'):
        raise ValueError('Contradictory capture completeness')
    if dropped or props['complete']!='yes':
        raise ValueError('Incomplete PRG capture cannot certify evidence')
    result=audit(path)
    actual=sum(result['event_counts'].values())
    if actual!=int(props['events_recorded']):
        raise ValueError('Capture event count mismatch')
    result['capture_metadata_verified']=True
    result['capture_complete']=True
    result['events_recorded']=actual
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace',type=Path)
    p.add_argument('--out',type=Path)
    p.add_argument('--meta',type=Path)
    args=p.parse_args()
    result=audit_verified(args.trace,args.meta or args.trace.with_suffix('.meta.txt'))
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
