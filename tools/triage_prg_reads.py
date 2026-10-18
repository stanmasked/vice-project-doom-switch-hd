#!/usr/bin/env python3
"""Stage48: conservative triage of PRG read runs, not code/data classification."""
import argparse
import json
from pathlib import Path
from group_prg_read_ranges import runs

def triage(trace, meta, min_run=2):
    source=runs(trace,meta,min_run)
    candidates=[]
    for candidate in source['candidate_runs']:
        candidates.append({
            **candidate,
            'role':'indeterminate_code_or_data',
            'confidence':'unclassified',
            'instruction_pc_observed':False,
            'operand_access_proven':False,
            'level_data_proven':False,
            'required_evidence':[
                'Same-session instruction PC and memory-access correlation',
                'Decode and verify the executing instruction and effective address',
                'Confirm the PRG bank mapping at instruction and read time',
                'Independent scene/PPU evidence before claiming level-data semantics'
            ]
        })
    return {
        'schema':1,
        'classification':'unclassified PRG-read candidates; CPU bus may include instruction fetches',
        'capture_metadata_verified':source['capture_metadata_verified'],
        'event_counts':source['event_counts'],
        'unresolved_reads':source['unresolved_reads'],
        'candidates':candidates,
        'confirmed_level_data_ranges':[],
        'limitations':source['limitations']+[
            'Stage45 does not log executing instruction PCs',
            'Contiguous or repeated reads alone cannot distinguish code fetches from data'
        ]
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace',type=Path)
    p.add_argument('--meta',type=Path)
    p.add_argument('--min-run',type=int,default=2)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    data=triage(a.trace,a.meta or a.trace.with_suffix('.meta.txt'),a.min_run)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
    print(json.dumps(data,indent=2))
if __name__=='__main__':main()
