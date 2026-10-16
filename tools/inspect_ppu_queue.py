#!/usr/bin/env python3
"""ROM-local static inspection of the 6502 NMI/PPU command queue.

No original ROM, raw opcode dump, video payload or game assets are committed.
A successful static decode does not establish the live first-stage PPU state.
"""
import argparse,json
from pathlib import Path
from inspect_rom import parse_rom
from disassemble_fixed_bank import decode

BASE=0xE609
DISPATCH=0xE612
LOW=0xE61B
HIGH=0xE61C
SIGNATURES={
  0xE5DC:'LDA #$3C',0xE5DE:'STA $04',0xE5E2:'LDA $0600,Y',
  0xE5E5:'BEQ $E5F9',0xE5E7:'TAX',0xE5E8:'LDA $04',
  0xE5EA:'SEC',0xE5EB:'SBC $E609,X',0xE5EE:'BCC $E5F9',
  0xE5F0:'STA $04',0xE5F2:'TXA',0xE5F3:'JSR $E612',
  0xE5F6:'JMP $E5E0',0xE612:'ASL A',0xE613:'TAX',
  0xE614:'LDA $E61C,X',0xE617:'PHA',0xE618:'LDA $E61B,X',
  0xE61B:'PHA',0xE61C:'RTS'
}

def inspect(prg,strict=True):
    if len(prg)<8192 or len(prg)%8192:
        raise ValueError('PRG must be multiple of 8KiB')
    bank=prg[-8192:]
    anchors={}
    for pc,asm in SIGNATURES.items():
        instruction=decode(bank,pc)
        anchors['%04X'%pc]=bool(instruction and instruction['asm']==asm)
    if strict and not all(anchors.values()):
        raise ValueError('Dispatcher signature mismatch at '+str([p for p,v in anchors.items() if not v]))
    command_count=DISPATCH-BASE-1
    commands=[]
    for command_id in range(1,command_count+1):
        cost=bank[BASE+command_id-0xE000]
        low=bank[LOW+2*command_id-0xE000]
        high=bank[HIGH+2*command_id-0xE000]
        stack_return=low|(high<<8)
        handler=(stack_return+1)&0xFFFF
        opcode=decode(bank,handler)
        commands.append({
            'command_id':command_id,
            'budget_units':cost,
            'stack_return_address':'0x%04X'%stack_return,
            'handler_entry':'0x%04X'%handler,
            'handler_first_opcode_decodable':bool(opcode)
        })
    if strict and any(v['budget_units']==0 or not v['handler_first_opcode_decodable'] for v in commands):
        raise ValueError('Unusable command cost or handler opcode')
    return {
        'method':'static fixed-bank decoding; NOT a runtime game trace',
        'queue_base':'$0600','queue_index_ram':'$16',
        'frame_budget_units':60,
        'command_id_range':[1,command_count],
        'command_count':command_count,
        'distinct_handler_count':len({x['handler_entry'] for x in commands}),
        'dispatcher_code_anchors':anchors,'commands':commands,
        'limitations':[
            'Queued command payload formats and actual stage data are not decoded',
            'The byte-table values are cost/budget units, not proven CPU cycles',
            'Live command usage and PPU palettes require tracing the original ROM',
            'An inferred handler pointer is not proof of runtime reachability'
        ]
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom')
    p.add_argument('--out',help='Local-only report path within ignored private/')
    p.add_argument('--summary-only',action='store_true')
    args=p.parse_args()
    rom=parse_rom(args.rom)
    if rom['mapper']!=4:p.error('MMC3 mapper 4 is required')
    report=inspect(rom['prg'])
    if args.out:
        dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    if args.summary_only:report.pop('commands')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
