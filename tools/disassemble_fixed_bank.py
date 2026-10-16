#!/usr/bin/env python3
"""Conservative 6502 control-flow static pass over MMC3 fixed E000-FFFF PRG bank.
No emulation, no runtime guarantees. Only official 6502 opcodes followed.
"""
from pathlib import Path
import argparse
import collections
import json

# Mode syntax: imp acc imm zp zpx zpy abs absx absy indx indy ind rel
SPECS={
'ADC':{'imm':0x69,'zp':0x65,'zpx':0x75,'abs':0x6d,'absx':0x7d,'absy':0x79,'indx':0x61,'indy':0x71},
'AND':{'imm':0x29,'zp':0x25,'zpx':0x35,'abs':0x2d,'absx':0x3d,'absy':0x39,'indx':0x21,'indy':0x31},
'ASL':{'acc':0x0a,'zp':0x06,'zpx':0x16,'abs':0x0e,'absx':0x1e},
'BCC':{'rel':0x90}, 'BCS':{'rel':0xb0}, 'BEQ':{'rel':0xf0}, 'BMI':{'rel':0x30},
'BNE':{'rel':0xd0}, 'BPL':{'rel':0x10}, 'BVC':{'rel':0x50}, 'BVS':{'rel':0x70},
'BIT':{'zp':0x24,'abs':0x2c},'BRK':{'imp':0x00},
'CLC':{'imp':0x18},'CLD':{'imp':0xd8},'CLI':{'imp':0x58},'CLV':{'imp':0xb8},
'CMP':{'imm':0xc9,'zp':0xc5,'zpx':0xd5,'abs':0xcd,'absx':0xdd,'absy':0xd9,'indx':0xc1,'indy':0xd1},
'CPX':{'imm':0xe0,'zp':0xe4,'abs':0xec},'CPY':{'imm':0xc0,'zp':0xc4,'abs':0xcc},
'DEC':{'zp':0xc6,'zpx':0xd6,'abs':0xce,'absx':0xde},'DEX':{'imp':0xca},'DEY':{'imp':0x88},
'EOR':{'imm':0x49,'zp':0x45,'zpx':0x55,'abs':0x4d,'absx':0x5d,'absy':0x59,'indx':0x41,'indy':0x51},
'INC':{'zp':0xe6,'zpx':0xf6,'abs':0xee,'absx':0xfe},'INX':{'imp':0xe8},'INY':{'imp':0xc8},
'JMP':{'abs':0x4c,'ind':0x6c},'JSR':{'abs':0x20},
'LDA':{'imm':0xa9,'zp':0xa5,'zpx':0xb5,'abs':0xad,'absx':0xbd,'absy':0xb9,'indx':0xa1,'indy':0xb1},
'LDX':{'imm':0xa2,'zp':0xa6,'zpy':0xb6,'abs':0xae,'absy':0xbe},
'LDY':{'imm':0xa0,'zp':0xa4,'zpx':0xb4,'abs':0xac,'absx':0xbc},
'LSR':{'acc':0x4a,'zp':0x46,'zpx':0x56,'abs':0x4e,'absx':0x5e},
'NOP':{'imp':0xea},'ORA':{'imm':0x09,'zp':0x05,'zpx':0x15,'abs':0x0d,'absx':0x1d,'absy':0x19,'indx':0x01,'indy':0x11},
'PHA':{'imp':0x48},'PHP':{'imp':0x08},'PLA':{'imp':0x68},'PLP':{'imp':0x28},
'ROL':{'acc':0x2a,'zp':0x26,'zpx':0x36,'abs':0x2e,'absx':0x3e},
'ROR':{'acc':0x6a,'zp':0x66,'zpx':0x76,'abs':0x6e,'absx':0x7e},
'RTI':{'imp':0x40},'RTS':{'imp':0x60},
'SBC':{'imm':0xe9,'zp':0xe5,'zpx':0xf5,'abs':0xed,'absx':0xfd,'absy':0xf9,'indx':0xe1,'indy':0xf1},
'SEC':{'imp':0x38},'SED':{'imp':0xf8},'SEI':{'imp':0x78},
'STA':{'zp':0x85,'zpx':0x95,'abs':0x8d,'absx':0x9d,'absy':0x99,'indx':0x81,'indy':0x91},
'STX':{'zp':0x86,'zpy':0x96,'abs':0x8e},'STY':{'zp':0x84,'zpx':0x94,'abs':0x8c},
'TAX':{'imp':0xaa},'TAY':{'imp':0xa8},'TSX':{'imp':0xba},'TXA':{'imp':0x8a},'TXS':{'imp':0x9a},'TYA':{'imp':0x98},
}
OP={v:(key,mode) for key,m in SPECS.items() for mode,v in m.items()}
assert len(OP)==151
SIZES={'imp':1,'acc':1,'imm':2,'zp':2,'zpx':2,'zpy':2,'indx':2,'indy':2,'rel':2,'abs':3,'absx':3,'absy':3,'ind':3}
BRANCHES={'BCC','BCS','BEQ','BMI','BNE','BPL','BVC','BVS'}
TERMINATE={'RTS','RTI','BRK'}


def decode(bank, pc):
    if not 0xE000<=pc<=0xFFFF:return None
    off=pc-0xE000
    m=OP.get(bank[off])
    if not m:return None
    name,mode=m;size=SIZES[mode]
    if off+size>len(bank):return None
    raw=bank[off:off+size]
    operand=int.from_bytes(raw[1:],'little') if size>1 else None
    if mode=='rel':operand=(pc+2+int.from_bytes(raw[1:2],'little',signed=True))&0xffff
    fmt={'imp':'','acc':' A','imm':' #${:02X}','zp':' ${:02X}','zpx':' ${:02X},X','zpy':' ${:02X},Y',
        'indx':' (${:02X},X)','indy':' (${:02X}),Y','rel':' ${:04X}',
        'abs':' ${:04X}','absx':' ${:04X},X','absy':' ${:04X},Y','ind':' (${:04X})'}[mode]
    asm=name+(fmt.format(operand) if operand is not None else fmt)
    return dict(pc=pc,op=bank[off],name=name,mode=mode,size=size,raw=raw.hex(' ').upper(),operand=operand,asm=asm)


def follow(bank, vectors):
    work=collections.deque((pc,who) for who,pc in vectors.items())
    seen={}; owners=collections.defaultdict(set); outside=set(); undecoded=set()
    while work:
        pc,owner=work.popleft()
        if not 0xE000<=pc<=0xFFFF:
            outside.add((owner,pc));continue
        if pc in seen:
            owners[pc].add(owner);continue
        op=decode(bank,pc)
        if op is None:
            undecoded.add((owner,pc));continue
        seen[pc]=op;owners[pc].add(owner)
        next_pc=pc+op['size']
        if op['name'] in BRANCHES:
            work.extend(((op['operand'],owner),(next_pc,owner)))
        elif op['name']=='JSR':
            work.extend(((op['operand'],owner),(next_pc,owner)))
        elif op['name']=='JMP':
            if op['mode']=='abs':work.append((op['operand'],owner))
        elif op['name'] not in TERMINATE and next_pc<=0xffff:
            work.append((next_pc,owner))
    return seen,owners,outside,undecoded


def main():
    p=argparse.ArgumentParser();p.add_argument('rom');p.add_argument('--out',default='.');arg=p.parse_args()
    b=Path(arg.rom).read_bytes();h=b[:16]
    if b[:4]!=b'NES\x1a' or (h[6]>>4)|(h[7]&0xF0)!=4 or h[4]!=8:
        raise ValueError('Expected MMC3/128KiB PRG ROM')
    prg=b[16+(512 if h[6]&4 else 0):][:128*1024]
    bank=prg[-8192:]
    vectors={n:int.from_bytes(prg[-offset:-offset+2 if offset!=2 else None],'little') for n,offset in [('NMI',6),('RESET',4),('IRQ',2)]}
    ins,owners,outside,undecoded=follow(bank,vectors)
    directory=Path(arg.out);directory.mkdir(parents=True,exist_ok=True)
    lines=[f'Vectors: '+', '.join(f'{k}=${v:04X}' for k,v in vectors.items()),
        'CPU map: $E000-$FFFF = last 8KiB PRG bank (MMC3 fixed bank, under normal mapping)',
        'Analysis: recursive walk of legal 6502 instructions, NOT an emulator or runtime trace.',
        f'Visited {len(ins)} unique addresses, exited bank to {len(outside)} distinct owner/addresses, stopped at {len(undecoded)} illegal decode addresses.',
        '', 'ORDERED REACHABLE CODE:']
    for pc,op in sorted(ins.items()):
        lines.append(f"${pc:04X}  {op['raw']:<8} {op['asm']}")
    lines.extend(['','OUTSIDE FIXED BANK TARGETS (bank-dependent, must not resolve statically):'])
    for src,a in sorted(outside):lines.append(f'{src:5s} ${a:04X}')
    lines.extend(['','DECODE STOPS (could be data or undocumented instruction):'])
    for src,a in sorted(undecoded):lines.append(f'{src:5s} ${a:04X}')
    (directory/'fixed_bank_disassembly.txt').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print('Vectors:',vectors)
    print('Reachable official opcodes:',len(ins),'outside:',len(outside),'decode stops:',len(undecoded))
    for entry,pc in vectors.items():
        print(f'\n{entry} ${pc:04X}:')
        for j in range(28):
            op=decode(bank,pc)
            if not op:
                print(f'  ${pc:04X}: (not recognized official opcode)');break
            print(f"  ${pc:04X} {op['raw']:<8} {op['asm']}")
            pc+=op['size']
            if op['name'] in ('RTI','RTS','JMP'):break
    mmc3={0x8000,0x8001,0xa000,0xa001,0xc000,0xc001,0xe000,0xe001}
    mmc_hits=[op for op in ins.values() if op['mode']=='abs' and op['operand'] in mmc3 and op['name'].startswith('ST')]
    counts=collections.Counter(f"${op['operand']:04X}" for op in mmc_hits)
    (directory/'fixed_bank_6502_summary.json').write_text(json.dumps({
      'vectors':{k:f'0x{v:04X}' for k,v in vectors.items()},
      'reachable_instructions':len(ins),'unresolved_external_targets':len(outside),
      'illegal_decode_stops':len(undecoded),
      'mapper_register_store_counts_static':dict(counts),
      'mapper_register_store_locations_static':[f"${op['pc']:04X} {op['asm']}" for op in sorted(mmc_hits,key=lambda x:x['pc'])]},indent=2),encoding='utf8')

if __name__=='__main__':main()
