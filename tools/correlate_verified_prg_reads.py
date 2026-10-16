#!/usr/bin/env python3
"""Stage58: require local PRG byte agreement before reporting read candidates."""
import argparse
import json
from pathlib import Path
from verify_6502_prg_instruction import verify
from compare_6502_read_candidates import compare

def correlate(trace, meta, prg, *, exec_seq, opcode_hex, max_gap=3,
              zp_low=None, zp_high=None):
    proven_bytes=verify(trace,meta,prg,exec_seq=exec_seq,
                        instruction_hex=opcode_hex)
    if not proven_bytes['bytes_match']:
        return {'schema':1,'status':'instruction_not_verified',
                'verification':proven_bytes,'candidate_reads':[],
                'instruction_caused_read_proven':False,
                'level_data_proven':False}
    candidates=compare(trace,meta,exec_seq=exec_seq,opcode_hex=opcode_hex,
                       max_gap=max_gap,zp_low=zp_low,zp_high=zp_high)
    return {'schema':1,'status':'local_instruction_bytes_match',
            'verification':proven_bytes,
            'calculation':candidates['calculation'],
            'candidate_reads':candidates['candidate_reads'],
            'search_stopped_by':candidates['search_stopped_by'],
            'instruction_caused_read_proven':False,
            'level_data_proven':False,
            'limitations':[
                'Local PRG image identity is not independently authenticated',
                'Sparse EXEC hook timing cannot establish read causality',
                'CPU read values and original level identity remain unverified'
            ]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace',type=Path)
    p.add_argument('--meta',type=Path)
    p.add_argument('--prg',type=Path,required=True)
    p.add_argument('--exec-seq',type=int,required=True)
    p.add_argument('--instruction-hex',required=True)
    p.add_argument('--max-gap',type=int,default=3)
    p.add_argument('--zp-low',type=lambda s:int(s,16))
    p.add_argument('--zp-high',type=lambda s:int(s,16))
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    result=correlate(a.trace,a.meta or a.trace.with_suffix('.meta.txt'),a.prg,
                    exec_seq=a.exec_seq,opcode_hex=a.instruction_hex,
                    max_gap=a.max_gap,zp_low=a.zp_low,zp_high=a.zp_high)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
