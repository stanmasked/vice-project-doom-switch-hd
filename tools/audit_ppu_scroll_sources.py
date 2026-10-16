#!/usr/bin/env python3
"""Static PPU scroll-source audit for a user-owned MMC3 ROM.

Validates 6502 opcode anchors, not runtime camera or collision geometry.
Never publish ROM bytes, game tile data, or private reports.
"""
import argparse
import hashlib
import json
from pathlib import Path

BANK_BYTES=8192
EMITTER=(
 (0xE8DE,(0xA5,0x0C),'LDA $0C','PPUCTRL nametable source'),
 (0xE8E0,(0x29,0x01),'AND #$01','Nametable bit'),
 (0xE8E2,(0x05,0x00),'ORA $00','Other PPUCTRL bits'),
 (0xE8E4,(0x8D,0x00,0x20),'STA $2000','Write PPUCTRL'),
 (0xE8E7,(0xAD,0x02,0x20),'LDA $2002','Reset PPUSCROLL write latch'),
 (0xE8EA,(0xA5,0x0B),'LDA $0B','First scroll source'),
 (0xE8EC,(0x8D,0x05,0x20),'STA $2005','First PPUSCROLL write'),
 (0xE8EF,(0xA5,0x0D),'LDA $0D','Second scroll source'),
 (0xE8F1,(0x8D,0x05,0x20),'STA $2005','Second PPUSCROLL write'),
 (0xE8F4,(0x60,),'RTS','Return'),
)
CALL=(0xE89D,(0x20,0xDE,0xE8),'JSR $E8DE')
PORTS={0x2000:'PPUCTRL',0x2005:'PPUSCROLL',0x2006:'PPUADDR'}
STORES={0x8D:'STA',0x8E:'STX',0x8C:'STY'}

def address(bank,offset):
    if not 0<=bank<16 or not 0<=offset<BANK_BYTES:
        raise ValueError('Invalid bank/offset')
    return '$'+'{:04X}'.format(0xE000+offset) if bank==15 else None

def store_candidates(prg):
    if len(prg)!=16*BANK_BYTES:raise ValueError('Expected 128KiB PRG')
    report=[]
    for bank in range(16):
        data=prg[bank*BANK_BYTES:(bank+1)*BANK_BYTES]
        hits=[]
        for pos in range(BANK_BYTES-2):
            op=data[pos]
            if op not in STORES:continue
            addr=data[pos+1]|(data[pos+2]<<8)
            if addr not in PORTS:continue
            hits.append({'offset_in_bank':pos,'cpu_address_if_fixed':address(bank,pos),
                         'candidate_instruction':STORES[op]+' $'+'{:04X}'.format(addr),
                         'register':PORTS[addr]})
        report.append({'prg_bank':bank,'byte_pattern_count':len(hits),'matches':hits})
    return report

def inspect(prg,strict=True):
    if len(prg)!=16*BANK_BYTES:raise ValueError('Expected exact 128KiB PRG')
    fixed=prg[-BANK_BYTES:]
    evidence=[]
    bad=[]
    for pc,raw,asm,meaning in EMITTER:
        valid=tuple(fixed[pc-0xE000:pc-0xE000+len(raw)])==raw
        evidence.append({'cpu_address':'$'+'{:04X}'.format(pc),'asm':asm,
                         'purpose':meaning,'opcode_verified':valid})
        if not valid:bad.append('$'+'{:04X}'.format(pc))
    caller,op,asm=CALL
    call_ok=tuple(fixed[caller-0xE000:caller-0xE000+len(op)])==op
    if not call_ok:bad.append('$'+'{:04X}'.format(caller)+' (caller)')
    if bad and strict:raise ValueError('Scroll instruction anchor mismatch at '+', '.join(bad))
    scans=store_candidates(prg)
    writes=[m for m in scans[15]['matches'] if m['register']=='PPUSCROLL']
    if strict:
        for pc in (0xE8EC,0xE8F1):
            if not any(m['cpu_address_if_fixed']=='$'+'{:04X}'.format(pc) and
                       m['candidate_instruction']=='STA $2005' for m in writes):
                raise ValueError('PPUSCROLL emitter missing')
    return {
      'schema':1,'method':'strict 6502 code anchors and conservative PRG byte scan',
      'prg_sha256':hashlib.sha256(prg).hexdigest(),
      'fixed_bank_mapping':'$E000-$FFFF in normal MMC3 mode',
      'scroll_emitter_start':'$E8DE',
      'caller':{'address':'$'+'{:04X}'.format(caller),'asm':asm,
                'opcode_verified':call_ok},
      'audited_instructions':evidence,
      'all_emitter_anchors_verified':not bad,
      'scroll_sources':{'first_PPUSCROLL_write':'zero-page $0B',
                        'second_PPUSCROLL_write':'zero-page $0D',
                        'PPUCTRL_low_nametable_bit':'zero-page $0C & 1',
                        'PPUCTRL_other_bits':'zero-page $00'},
      'fixed_bank_ppuscroll_candidates':writes,
      'prg_bank_register_write_candidate_counts':[
          {'bank':b['prg_bank'],'pattern_count':b['byte_pattern_count']} for b in scans],
      'limitations':[
          'PPUSCROLL RAM sources are not automatically game-world camera coordinates',
          'Other raster IRQ writers can change PPU scroll within a frame',
          'Pattern matches may be data or unreachable code',
          'Switchable PRG bank offsets do not have a fixed CPU address',
          'No first-stage collisions, entities or camera write origin recovered']
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom',type=Path)
    p.add_argument('--out',type=Path,default=Path('private/stage33_scroll_audit.json'))
    p.add_argument('--non-strict',action='store_true')
    args=p.parse_args()
    raw=args.rom.read_bytes()
    if len(raw)<16 or raw[:4]!=b'NES\x1a':p.error('Not an NES image')
    h=raw[:16]
    start=16+(512 if h[6]&4 else 0)
    mapper=(h[6]>>4)|(h[7]&0xF0)
    if mapper!=4 or h[4]!=8 or len(raw)<start+128*1024:
        p.error('Expected mapper 4 and 128KiB PRG')
    result=inspect(raw[start:start+128*1024],strict=not args.non_strict)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({
        'anchors_verified':result['all_emitter_anchors_verified'],
        'first_scroll_source':result['scroll_sources']['first_PPUSCROLL_write'],
        'second_scroll_source':result['scroll_sources']['second_PPUSCROLL_write'],
        'fixed_bank_scroll_candidates':len(result['fixed_bank_ppuscroll_candidates']),
        'report':str(args.out),
        'warning':'Not a recovered first-level camera or collision map'},indent=2))

if __name__=='__main__':main()
