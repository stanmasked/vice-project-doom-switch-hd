#!/usr/bin/env python3
"""Stage57: compare instruction bytes to a LOCAL 128 KiB raw PRG image.

No original ROM data is written to reports or Git. Physical bank mapping
is replayed from stage53, and bank-boundary instructions are rejected.
"""
import argparse
import csv
import json
from pathlib import Path
from validate_joint_cpu_context import validate
from analyze_dispatch_execution import mapping

PRG_BYTES=16*8192

def verify(trace, meta, prg, *, exec_seq, instruction_hex):
    validate(trace,meta)
    with Path(trace).open(newline='',encoding='utf8') as f:
        rows=list(csv.DictReader(f,delimiter='\t'))
    if type(exec_seq) is not int or not 1<=exec_seq<=len(rows):
        raise ValueError('Invalid EXEC event sequence')
    if rows[exec_seq-1]['kind']!='EXEC':
        raise ValueError('Selected event is not EXEC')
    try:
        claimed=bytes.fromhex(instruction_hex)
    except (TypeError,ValueError) as e:
        raise ValueError('Invalid instruction bytes') from e
    if not 1<=len(claimed)<=3:
        raise ValueError('Only 1-3 instruction bytes accepted')
    image=Path(prg).read_bytes()
    if len(image)!=PRG_BYTES:
        raise ValueError('Expected exactly 128 KiB raw PRG (headerless, no CHR)')
    selected=r6=r7=None
    for row in rows[:exec_seq]:
        kind=row['kind']
        if kind=='SELECT':selected=int(row['value'],16)
        elif kind=='DATA' and selected is not None:
            v=int(row['value'],16)
            if selected%8==6:r6=v
            if selected%8==7:r7=v
    event=rows[exec_seq-1]
    pc=int(event['address'],16)
    bank,_=mapping(pc,selected,r6,r7)
    if bank is None:
        return {'status':'unresolved_bank','bytes_match':False,
                'instruction_causality_proven':False}
    within=pc&0x1FFF
    if within+len(claimed)>8192:
        return {'status':'crosses_bank_window_unverified','bytes_match':False,
                'instruction_causality_proven':False}
    offset=bank*8192+within
    match=image[offset:offset+len(claimed)]==claimed
    return {'status':'matched_local_prg' if match else 'byte_mismatch',
            'bytes_match':match,'cpu_pc':f'{pc:04X}',
            'physical_bank':bank,'physical_offset':offset,
            'instruction_causality_proven':False,
            'level_data_proven':False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace',type=Path)
    p.add_argument('--meta',type=Path)
    p.add_argument('--prg',type=Path,required=True)
    p.add_argument('--exec-seq',type=int,required=True)
    p.add_argument('--instruction-hex',required=True)
    a=p.parse_args()
    print(json.dumps(verify(a.trace,a.meta or a.trace.with_suffix('.meta.txt'),
                            a.prg,exec_seq=a.exec_seq,
                            instruction_hex=a.instruction_hex),indent=2))
if __name__=='__main__':main()
