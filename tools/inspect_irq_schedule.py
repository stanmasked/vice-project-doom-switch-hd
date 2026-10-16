#!/usr/bin/env python3
"""Static analysis of Vice: Project Doom MMC3 IRQ dispatcher.

Writes game-derived record values only to local output. Never commit reports.
This does NOT emulate the NES or prove which table rows run during gameplay.
"""
import argparse
import collections
import json
from pathlib import Path
from inspect_rom import parse_rom
from disassemble_fixed_bank import decode

START = 0xE10D
END = 0xE1DA
WIDTH = 5
# Known USA ROM instruction anchors; they connect the rows to executable code.
ANCHORS = {
    0xE0B0: 'A5 36 AA 29 01 F0 2B',
    0xE0B8: '4A 85 33 0A 0A 18 65 33 AA',
    0xE0C1: 'BD 0F E1',
    0xE0C4: '8D 00 C0',
    0xE0C7: '8D 01 C0',
    0xE0CA: '8D 01 E0',
    0xE0CD: 'BD 0D E1 85 34',
    0xE0D2: 'BD 0E E1 85 35',
    0xE0D7: 'BD 11 E1 85 38',
    0xE0DC: 'BD 10 E1 85 33',
    0xE1F3: '6C 34 00',
    0xE0E6: 'A5 33 0A 0A 18 65 33 AA',
    0xE0EE: 'BD 0F E1 8D 00 C0',
    0xE0F4: 'BD 0D E1 85 34',
    0xE0F9: 'BD 0E E1 85 35',
    0xE0FE: 'BD 10 E1 85 33',
    0xE103: 'A5 38 85 37',
    0xE107: 'BD 11 E1 85 38',
    0xE392: 'A6 37 CA D0 FD 60',
    0xE398: 'A6 38 CA D0 FD 60'
}

def last_bank(prg):
    if len(prg) < 8192 or len(prg) % 8192:
        raise ValueError('PRG must end on an 8KiB bank')
    return prg[-8192:]

def validate_anchors(bank):
    failures = []
    for cpu, hexdump in ANCHORS.items():
        signature = bytes.fromhex(hexdump)
        if bank[cpu-0xE000:cpu-0xE000+len(signature)] != signature:
            failures.append('CPU 0x%04X' % cpu)
    return failures

def extract_rows(bank, start=START, end=END):
    if len(bank) != 8192:
        raise ValueError('Expected a fixed 8KiB bank')
    if not (0xE000 <= start < end <= 0x10000) or (end-start)%WIDTH:
        raise ValueError('Invalid 5-byte record boundaries')
    rows = []
    for n, cpu in enumerate(range(start, end, WIDTH)):
        v = bank[cpu-0xE000:cpu-0xE000+WIDTH]
        rows.append({
            'index': n, 'cpu_address': f'0x{cpu:04X}',
            'handler': f'0x{int.from_bytes(v[:2],"little"):04X}',
            'mmc3_irq_latch': v[2],
            'ram_0033': v[3], 'ram_0038': v[4]
        })
    return rows

def transition_graph(rows):
    """Link every row via the RAM $33 'next record' field.

    Static graph topology is NOT a proof that all graph edges execute.
    """
    links=[r['ram_0033'] for r in rows]
    length=len(links)
    bad=[i for i,value in enumerate(links) if value>=length]
    if bad:
        return {'invalid_next_indices':bad,'zero_indegree':[],'cycles':[]}
    indegree=[0]*length
    for value in links:
        indegree[value]+=1
    cycles=set()
    for start in range(length):
        seen={}
        path=[]
        cur=start
        while cur not in seen:
            seen[cur]=len(path)
            path.append(cur)
            cur=links[cur]
        cycle=path[seen[cur]:]
        idx=cycle.index(min(cycle))
        cycles.add(tuple(cycle[idx:]+cycle[:idx]))
    return {'invalid_next_indices':[],
            'zero_indegree':[i for i,degree in enumerate(indegree) if degree==0],
            'cycles':[list(item) for item in sorted(cycles)]}

def inspect(prg, strict=False):
    bank = last_bank(prg)
    failures = validate_anchors(bank)
    if int.from_bytes(bank[-2:], 'little') != END:
        failures.append('IRQ vector differs from table end')
    if strict and failures:
        raise ValueError('Known-version anchor mismatch: ' + ', '.join(failures))
    rows = extract_rows(bank)
    counts = collections.Counter(row['handler'] for row in rows)
    bad = [row['index'] for row in rows
           if not (0xE000 <= int(row['handler'],16) <= 0xFFFF and
                   decode(bank, int(row['handler'],16)) is not None)]
    if strict and bad:
        raise ValueError('Invalid handler opcodes at row indices: ' + str(bad))
    return {
        'method':'static analysis; not a runtime trace',
        'table_start':f'0x{START:04X}', 'table_end_exclusive':f'0x{END:04X}',
        'row_width':WIDTH, 'table_bytes':END-START,
        'row_count':len(rows), 'unique_handlers':len(counts),
        'handlers':dict(sorted(counts.items())),
        'validated_instruction_anchors':len(ANCHORS),
        'anchor_mismatches':failures, 'undecodable_handler_indices':bad,
        'rows':rows,
        'transition_graph':transition_graph(rows),
        'uncertainties':[
            'Graph edges are possible transitions, not verified runtime paths',
            'Row byte +3 is next-row index ($33); byte +4 is used by busy-wait counters ($38/$37)',
            'Inferred table end is contiguous with IRQ entrypoint',
        ]
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom',help='Locally held original NES ROM')
    parser.add_argument('--strict',action='store_true')
    parser.add_argument('--summary-only',action='store_true')
    parser.add_argument('--out',help='Local JSON report path (ignored by Git)')
    args=parser.parse_args()
    rom=parse_rom(args.rom)
    if rom['mapper'] != 4:
        parser.error('Expected NES MMC3 mapper 4')
    result=inspect(rom['prg'],strict=args.strict)
    if args.out:
        dest=Path(args.out)
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    if args.summary_only:
        result=dict(result)
        result.pop('rows')
        result.pop('handlers')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
