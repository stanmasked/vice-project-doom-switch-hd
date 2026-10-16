#!/usr/bin/env python3
"""Static MMC3 CHR bank / NMI PPU-pipeline auditor for the owner's local ROM.

Only independently written analysis code and synthetic tests belong in GitHub.
No ROM-derived graphics, binaries or stage data are bundled.
"""
import argparse
import json
from pathlib import Path
from disassemble_fixed_bank import decode
from inspect_rom import parse_rom

CHR_ROUTINES=(0xE8A3,0xE8B8)
EXPECTED_SOURCES={0:0x3D,1:0x3E,2:0x3F,3:0x40,4:0x41,5:0x42}
EVIDENCE={
    'reset_chr_r0':(0xE588,'LDA #$00',0xE58C,'STA $3D'),
    'reset_chr_r1':(0xE58E,'LDA #$02',0xE590,'STA $3E'),
    'nmi_oam_dma':(0xE5AC,'LDA #$07',0xE5AE,'STA $4014'),
    'nmi_vram_queue_call':(0xE5B8,'JSR $E5DC',0xE5BB,'JSR $E7C3'),
    'nmi_irq_schedule_call':(0xE5BE,'JSR $E0B0',None,None),
    'vram_queue_head':(0xE5E2,'LDA $0600,Y',0xE5E5,'BEQ $E5F9'),
    'vram_queue_ppu_addr':(0xE63A,'STA $2006',0xE63D,'STX $2006'),
    'vram_queue_ppu_data':(0xE646,'STA $2007',None,None),
    'video_dispatch_start':(0xE7C3,'LDA $01',0xE7C5,'STA $2001'),
    'video_chr_regs_2_through_5':(0xE8A0,'JSR $E8B8',None,None),
}

def fixed_bank(prg):
    if len(prg)<8192 or len(prg)%8192:
        raise ValueError('PRG must be aligned to 8KiB')
    return prg[-8192:]

def trace_chr_selects(bank, start, instruction_limit=64):
    """Symbolically evaluate a straight-line code segment; do not follow branches."""
    if len(bank)!=8192:raise ValueError('Expected 8KiB bank')
    pc=start
    a=x=selection=None
    result=[]
    for _ in range(instruction_limit):
        ins=decode(bank,pc)
        if not ins:raise ValueError('Undecodable opcode at %04X'%pc)
        n,m,v=ins['name'],ins['mode'],ins['operand']
        if n=='RTS':
            if selection is not None:raise ValueError('Unpaired selection at return')
            return result
        if n=='LDA' and m in ('imm','zp'):
            a=v if m=='imm' else ('ram',v)
        elif n=='LDX' and m=='imm':
            x=v
        elif n=='INX' and m=='imp' and x is not None:
            x=(x+1)&255
        elif n=='STX' and m=='abs' and v==0x8000 and x is not None:
            if selection is not None:raise ValueError('Unpaired bank select')
            selection=x
        elif n=='STA' and m=='abs' and v==0x8001:
            if selection is None or a is None:raise ValueError('Data without bank register')
            result.append((selection,a))
            selection=None
        else:
            raise ValueError('Unsupported instruction at %04X: %s'%(pc,ins['asm']))
        pc+=ins['size']
    raise ValueError('Instruction bound exceeded')

def chr_1k_slots(registers,inversion,chr_1k_count=128):
    """Return 8 ordered PPU 1KiB slots following MMC3 CHR mapping rules."""
    if len(registers)!=6 or chr_1k_count<=0 or chr_1k_count&(chr_1k_count-1):
        raise ValueError('Expected six registers and power-of-two CHR bank count')
    a,b=registers[0]&0xFE,registers[1]&0xFE
    slots=[a,a+1,b,b+1,registers[2],registers[3],registers[4],registers[5]]
    if inversion: slots=slots[4:]+slots[:4]
    return [int(value)&(chr_1k_count-1) for value in slots]

def inspect(prg,chr_bytes,strict=True):
    bank=fixed_bank(prg)
    writes=[]
    for addr in CHR_ROUTINES: writes+=trace_chr_selects(bank,addr)
    sources={}
    for selector,symbol in writes:
        if selector&0xC0 or not 0<=selector<=5 or selector in sources:
            raise ValueError('Unexpected MMC3 CHR register selection')
        if not isinstance(symbol,tuple) or symbol[0]!='ram':
            raise ValueError('Bank ID is not zero-page RAM')
        sources[selector]=symbol[1]
    if strict and sources!=EXPECTED_SOURCES:
        raise ValueError('CHR mapping differs from audited ROM')
    evidence={}
    for key,(a,asmb,b,asmb2) in EVIDENCE.items():
        first=decode(bank,a)
        second=decode(bank,b) if b is not None else None
        evidence[key]=bool(first and first['asm']==asmb and (asmb2 is None or (second and second['asm']==asmb2)))
    if strict and not all(evidence.values()):
        raise ValueError('Instruction anchors changed: '+str([k for k,v in evidence.items() if not v]))
    if chr_bytes<=0 or chr_bytes%1024:
        raise ValueError('CHR size must be divisible by 1KiB')
    return {
        'method':'static code analysis; not scene-specific live memory capture',
        'chr_1k_banks_in_cart':chr_bytes//1024,
        'chr_register_zero_page_sources':{'R%d'%k:'$%02X'%v for k,v in sorted(sources.items())},
        'register_write_entrypoints':['0x%04X'%a for a in CHR_ROUTINES],
        'reset_chr_r0_r1_ram_values':[0,2] if evidence['reset_chr_r0'] and evidence['reset_chr_r1'] else None,
        'validated_nmi_ppu_evidence':evidence,
        'nmi_command_queue_base':'$0600',
        'limitations':[
            'Only two boot-time CHR RAM values recovered; stage-time registers unverified',
            'MMC3 register 0/1 select even-aligned 2KiB pairs; CHR inversion can rearrange PPU slots',
            'Palette, nametable, stage metatiles and live sprite animation not yet reconstructed'
        ]}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom')
    parser.add_argument('--out',help='Write local-only report (ignored private/ directory)')
    parser.add_argument('--registers',help='Six observed hexadecimal bytes: 00,02,04,05,06,07')
    parser.add_argument('--chr-inversion',action='store_true')
    parser.add_argument('--non-strict',action='store_true')
    args=parser.parse_args()
    rom=parse_rom(args.rom)
    if rom['mapper']!=4:parser.error('Only MMC3 mapper 4 is supported')
    result=inspect(rom['prg'],len(rom['chr']),strict=not args.non_strict)
    if args.registers:
        try:
            regs=[int(s.strip().removeprefix('0x'),16) for s in args.registers.split(',')]
            if any(not 0<=n<=255 for n in regs):raise ValueError('Value outside byte range')
            result['input_registers']=regs
            result['input_chr_inversion']=args.chr_inversion
            result['hypothetical_ppu_bank_slots']=chr_1k_slots(regs,args.chr_inversion,len(rom['chr'])//1024)
        except ValueError as error:
            parser.error('Invalid --registers: '+str(error))
    output=json.dumps(result,indent=2)+'\n'
    if args.out:
        dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(output,encoding='utf8')
    print(output,end='')

if __name__=='__main__':main()
