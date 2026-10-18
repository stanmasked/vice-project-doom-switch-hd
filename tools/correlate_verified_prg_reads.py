#!/usr/bin/env python3
"""Stage58: require local PRG byte agreement before reporting read candidates."""
import argparse
import hashlib
import re
import json
from pathlib import Path
from verify_6502_prg_instruction import verify
from compare_6502_read_candidates import compare
from validate_joint_cpu_context import validate

def correlate(trace, meta, prg, *, exec_seq, opcode_hex, max_gap=3,
              zp_low=None, zp_high=None, expected_prg_sha256=None):
    # Validate event completeness before an early PRG hash mismatch return.
    # Otherwise damaged captures could be reported as ordinary image mismatches.
    validate(trace, meta)
    if expected_prg_sha256 is not None:
        if not isinstance(expected_prg_sha256,str) or not re.fullmatch(r'[0-9a-fA-F]{64}',expected_prg_sha256):
            raise ValueError('Invalid expected PRG SHA256')
        digest=hashlib.sha256(Path(prg).read_bytes()).hexdigest()
        if digest!=expected_prg_sha256.lower():
            return {'schema':1,'status':'prg_identity_mismatch',
                    'reason':'local_prg_sha256_does_not_match_expected',
                    'candidate_reads':[],'instruction_caused_read_proven':False,
                    'level_data_proven':False,'read_values_proven':False}

    proven_bytes=verify(trace,meta,prg,exec_seq=exec_seq,
                        instruction_hex=opcode_hex)
    if not proven_bytes['bytes_match']:
        return {'schema':1,'status':'instruction_not_verified',
                'verification':proven_bytes,
                'reason':proven_bytes['status'],'candidate_reads':[],
                'instruction_caused_read_proven':False,
                'level_data_proven':False,'read_values_proven':False}
    candidates=compare(trace,meta,exec_seq=exec_seq,opcode_hex=opcode_hex,
                       max_gap=max_gap,zp_low=zp_low,zp_high=zp_high)
    return {'schema':1,'status':'local_instruction_bytes_match',
            'verification':proven_bytes,
            'calculation':candidates['calculation'],
            'candidate_reads':candidates['candidate_reads'],
            'search_stopped_by':candidates['search_stopped_by'],
            'instruction_caused_read_proven':False,
            'level_data_proven':False,
            'read_values_proven':False,
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
    p.add_argument('--expected-prg-sha256')
    a=p.parse_args()
    result=correlate(a.trace,a.meta or a.trace.with_suffix('.meta.txt'),a.prg,
                    exec_seq=a.exec_seq,opcode_hex=a.instruction_hex,
                    max_gap=a.max_gap,zp_low=a.zp_low,zp_high=a.zp_high,
                    expected_prg_sha256=a.expected_prg_sha256)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
