#!/usr/bin/env python3
"""Fail-closed FCEUX execution-log audit with MMC3 R6/R7 replay.

Logged CPU PCs are not proof of stage identity, camera semantics or
original-game level geometry. Keep actual FCEUX logs private.
"""
import argparse
import collections
import csv
import json
import re
from pathlib import Path

FIELDS=['frame','seq','cpu_cycle','kind','cpu_address','value','mmc3_mode',
        'r6','r7','mapped_bank','mapping_status','ram_07','ram_90','ram_91',
        'ram_92','ram_aa','ram_ab','ram_a8','ram_a9']
FIXED={0xE479,0xE4E6,0xE4F3,0xE500,0xE50F,0xE519,0xE522,
       0xE8DE,0xE8EA,0xE8EF,0xE418}
BANKED={0x835B:12,0xC906:14,0xC138:14,0xC1C8:14}
TRACKED_RAM={0x07,0x90,0x91,0x92,0xAA,0xAB,0xA8,0xA9}
KINDS={'EXEC','RAM_WRITE','MMC3_SELECT','MMC3_DATA'}
REQUIRED_META={'format','rom_md5','execution_hooks_registered',
               'tracked_ram_write_hooks','events_recorded','events_dropped',
               'trace_complete','cycle_trace_available','initial_mmc3_mode',
               'mmc3_write_coverage',
               'initial_prg_r6','initial_prg_r7','execution_provenance'}

def numeric(value,label,lo=0,hi=10**15):
    if not value.isdecimal() or not lo<=int(value)<=hi:
        raise ValueError(f'Invalid {label}: {value!r}')
    return int(value)

def hx(value,label,width):
    if not re.fullmatch(r'[0-9A-F]{%d}'%width,value):
        raise ValueError(f'Invalid {label}: {value!r}')
    return int(value,16)

def byte(value,label):
    return None if value=='unknown' else hx(value,label,2)

def meta_parse(path):
    d={}
    for line in Path(path).read_text(encoding='utf8').splitlines():
        if not line:continue
        if '=' not in line:raise ValueError('Malformed metadata line')
        k,v=line.split('=',1)
        if k in d:raise ValueError('Duplicate metadata key')
        d[k]=v
    if not REQUIRED_META<=d.keys() or d['format']!='vice_stage38_execution_v1':
        raise ValueError('Unsupported or incomplete trace metadata')
    if not re.fullmatch(r'[a-fA-F0-9]{32}',d['rom_md5']):
        raise ValueError('Invalid ROM identity')
    if any(d[k]!='unknown' for k in
           ('initial_mmc3_mode','initial_prg_r6','initial_prg_r7')):
        raise ValueError('Unverified initial mapper state')
    if d['mmc3_write_coverage']!='full_8000_9fff_even_odd':
        raise ValueError('Incomplete MMC3 write hook coverage')
    if d['execution_provenance']!='registerexec_callbacks_not_source_disassembly':
        raise ValueError('Unknown provenance')
    if d['cycle_trace_available'] not in ('yes','no'):
        raise ValueError('Unknown cycle trace type')
    if d['trace_complete'] not in ('yes','no'):
        raise ValueError('Unknown completeness state')
    numeric(d['events_recorded'],'events_recorded')
    numeric(d['events_dropped'],'events_dropped')
    if (d['trace_complete']=='yes')!=(int(d['events_dropped'])==0):
        raise ValueError('Inconsistent completeness flag')
    return d

def mapping(pc,select,r6,r7):
    if pc>=0xE000:return 15,'fixed_last_bank'
    if select is None:return None,'unknown_mode'
    mode=(select>>6)&1
    if pc>=0xC000:
        if mode==0:return 14,'fixed_second_last_bank'
        return (r6%16,'mapped_r6') if r6 is not None else (None,'unknown_r6')
    if pc>=0xA000:
        return (r7%16,'mapped_r7') if r7 is not None else (None,'unknown_r7')
    if pc>=0x8000:
        if mode==1:return 14,'fixed_second_last_bank'
        return (r6%16,'mapped_r6') if r6 is not None else (None,'unknown_r6')
    return None,'not_prg_rom'

def analyze(trace_path,meta_path,allow_incomplete=False):
    meta=meta_parse(meta_path)
    if meta['trace_complete']!='yes' and not allow_incomplete:
        raise ValueError('Incomplete event log; use --allow-incomplete only for diagnostics')
    select=r6=r7=None
    previous_seq=previous_frame=None
    counts=collections.Counter()
    mapped=collections.Counter()
    pc_counts=collections.Counter()
    unknown=wrong_bank=pairings=pointer_writes=0
    setup_seen=False
    with Path(trace_path).open(newline='',encoding='utf8') as f:
        reader=csv.DictReader(f,delimiter='\t')
        if reader.fieldnames!=FIELDS:raise ValueError('Unexpected TSV schema')
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError('Bad TSV row shape')
            frame=numeric(row['frame'],'frame',0,10**9)
            seq=numeric(row['seq'],'sequence',1,10**9)
            if previous_seq is not None and seq!=previous_seq+1:
                raise ValueError('Lost/reordered event sequence')
            if previous_seq is None and seq!=1:raise ValueError('Trace must start at seq 1')
            if previous_frame is not None and frame<previous_frame:
                raise ValueError('Nonmonotonic frame order')
            previous_seq,previous_frame=seq,frame
            if row['cpu_cycle']=='unknown':
                if meta['cycle_trace_available']=='yes':raise ValueError('Missing cycle timestamp')
            else:
                if meta['cycle_trace_available']=='no':raise ValueError('Unexpected cycle timestamp')
                numeric(row['cpu_cycle'],'cycle',0,10**16)
            kind=row['kind']
            if kind not in KINDS:raise ValueError('Unknown event kind')
            pc=hx(row['cpu_address'],'address',4)
            value=byte(row['value'],'event value')
            if kind=='EXEC' and (pc not in FIXED and pc not in BANKED or value is not None):
                raise ValueError('Unexpected EXEC address or value')
            if kind=='RAM_WRITE' and (pc not in TRACKED_RAM or value is None):
                raise ValueError('Unexpected RAM write')
            if kind in ('MMC3_SELECT','MMC3_DATA'):
                if not (0x8000<=pc<=0x9FFF) or pc%2!=(0 if kind=='MMC3_SELECT' else 1) or value is None:
                    raise ValueError('Unexpected mapper event')
            if kind=='MMC3_SELECT':select=value
            if kind=='MMC3_DATA' and select is not None:
                if select%8==6:r6=value
                if select%8==7:r7=value
            mode='unknown' if select is None else str((select>>6)&1)
            if (row['mmc3_mode']!=mode or
                row['r6']!=(f'{r6:02X}' if r6 is not None else 'unknown') or
                row['r7']!=(f'{r7:02X}' if r7 is not None else 'unknown')):
                raise ValueError('MMC3 snapshot inconsistent with recorded register events')
            bank,status=mapping(pc,select,r6,r7)
            if row['mapped_bank']!=('unknown' if bank is None else str(bank)) or row['mapping_status']!=status:
                raise ValueError('Physical PRG mapping inconsistent with mapper event history')
            for field in FIELDS[11:]:byte(row[field],field)
            counts[kind]+=1
            if kind=='RAM_WRITE' and pc in (0xAA,0xAB):pointer_writes+=1
            if kind=='EXEC':
                pc_counts['$'+f'{pc:04X}']+=1
                if pc in BANKED:
                    if bank is None:unknown+=1
                    elif bank!=BANKED[pc]:wrong_bank+=1
                    else:mapped[f'{pc:04X}:bank{bank}']+=1
                if pc==0x835B and bank==12:setup_seen=True
                elif pc==0xC906 and bank==14 and setup_seen:
                    pairings+=1
                    setup_seen=False
    if (previous_seq or 0)!=int(meta['events_recorded']):
        raise ValueError('Metadata event count mismatch')
    return {
      'schema':1,
      'classification':'instrumented FCEUX callback sequence; stage context unverified',
      'rom_md5':meta['rom_md5'].lower(),
      'events_recorded':int(meta['events_recorded']),
      'events_dropped':int(meta['events_dropped']),
      'complete':meta['trace_complete']=='yes',
      'event_counts':dict(sorted(counts.items())),
      'execution_counts_by_cpu_pc':dict(sorted(pc_counts.items())),
      'candidate_physically_mapped_exec_hits':dict(sorted(mapped.items())),
      'banked_hits_with_unknown_mapping':unknown,
      'banked_hits_with_different_mapping':wrong_bank,
      'candidate_setup_before_decoder_observations':pairings,
      'pointer_ram_write_events':pointer_writes,
      'limitations':[
          'Observed PCs and mapper writes are not a full instruction trace',
          'Initial MMC3 R6/R7 is unknown until its writes are observed',
          'CPU PC plus bank mapping does not verify original instruction bytes',
          'Setup-before-decoder order does not prove pointer preservation',
          'RAM snapshots in write callbacks may be pre-write values',
          'First-level identity, camera, entities and collisions are unverified'
      ]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace',type=Path)
    p.add_argument('--meta',type=Path)
    p.add_argument('--out',type=Path,default=Path('private/stage38_execution_audit.json'))
    p.add_argument('--allow-incomplete',action='store_true')
    args=p.parse_args()
    meta=args.meta or args.trace.with_suffix('.meta.txt')
    result=analyze(args.trace,meta,args.allow_incomplete)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'events':result['events_recorded'],
          'mapped_candidate_hits':result['candidate_physically_mapped_exec_hits'],
          'incomplete':not result['complete'],'out':str(args.out)},indent=2))
if __name__=='__main__':main()
