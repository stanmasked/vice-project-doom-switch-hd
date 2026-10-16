#!/usr/bin/env python3
"""ROM-local 6502 audit of RAM $92 writers and one bounded wraparound path.

Verified instruction signatures do not prove first-stage execution.
Never commit original game ROMs, extracted table entries, or captures.
"""
import argparse
import hashlib
import json
from pathlib import Path

BANK=8192
PRG_BYTES=BANK*16
ANCHORS=(
 ('fixed_seed_21',15,0x0418,'A9 15 85 92 20 47 C1',
  'LDA #$15; STA $92; JSR $C147'),
 ('fixed_wrap_decrement',15,0x050F,'A6 92 D0 02 A2 16 CA 4C 22 E5',
  'LDX $92; BNE; LDX #$16; DEX; JMP $E522'),
 ('fixed_wrap_increment',15,0x0519,'A6 92 E0 15 90 02 A2 FF E8 86 92',
  'LDX $92; CPX #$15; BCC; LDX #$FF; INX; STX $92'),
 ('bank14_seed_147',14,0x0138,'A9 93 A0 11 85 92 B1 A8 85 95',
  'LDA #$93; LDY #$11; STA $92; LDA ($A8),Y; STA $95'),
 ('bank14_indirect_writer',14,0x01C8,'A0 17 B1 A8 85 90 C8 B1 A8 85 92',
  'LDY #$17; LDA ($A8),Y; STA $90; INY; LDA ($A8),Y; STA $92'),
 ('bank12_pointer_consumer',12,0x035B,'A5 92 0A 65 92 69 76 85 AA A9 00 69 83 85 AB',
  'LDA $92; ASL; ADC $92; ADC #$76; STA $AA; ADC #$83; STA $AB'),
)
DIRECT={0x85:'STA zp',0x86:'STX zp',0x84:'STY zp',0xE6:'INC zp',
        0xC6:'DEC zp',0x06:'ASL zp',0x46:'LSR zp',0x26:'ROL zp',0x66:'ROR zp'}
ABS={0x8D:'STA abs',0x8E:'STX abs',0x8C:'STY abs',0xEE:'INC abs',
     0xCE:'DEC abs',0x0E:'ASL abs',0x4E:'LSR abs',0x2E:'ROL abs',0x6E:'ROR abs'}
INDEXED={0x95:'STA zp,X',0x94:'STY zp,X',0x96:'STX zp,Y',
         0xF6:'INC zp,X',0xD6:'DEC zp,X'}

def read_prg(rom):
    if len(rom)<16 or rom[:4]!=b'NES\x1a':
        raise ValueError('Expected NES ROM header')
    h=rom[:16]
    mapper=(h[6]>>4)|(h[7]&0xf0)
    start=16+(512 if h[6]&4 else 0)
    if mapper!=4 or h[4]!=8 or len(rom)<start+PRG_BYTES:
        raise ValueError('Expected complete 128KiB MMC3 PRG')
    return rom[start:start+PRG_BYTES]

def verify(prg,strict=True):
    if len(prg)!=PRG_BYTES:raise ValueError('Expected exact 128KiB PRG')
    results=[]
    misses=[]
    for name,bank,offset,hexbytes,description in ANCHORS:
        sig=bytes.fromhex(hexbytes)
        good=prg[bank*BANK+offset:bank*BANK+offset+len(sig)]==sig
        results.append({'anchor':name,'physical_prg_bank':bank,
                        'offset_in_bank':offset,'signature_verified':good,
                        'description':description})
        if not good:misses.append(name)
    if misses and strict:raise ValueError('Writer anchor changed: '+', '.join(misses))
    return results

def direct_write_patterns(prg):
    """Potential writes by byte matching; includes data/unreachable candidates."""
    if len(prg)!=PRG_BYTES:raise ValueError('Expected 128KiB PRG')
    hits=[]
    for bank in range(16):
        buf=prg[bank*BANK:(bank+1)*BANK]
        for off in range(BANK-1):
            op=buf[off]
            if op in DIRECT and buf[off+1]==0x92:
                hits.append({'physical_prg_bank':bank,'offset_in_bank':off,
                             'opcode_pattern':DIRECT[op],
                             'status':'raw_literal_not_proven_executed'})
            elif off<BANK-2 and op in ABS and buf[off+1:off+3]==b'\x92\x00':
                hits.append({'physical_prg_bank':bank,'offset_in_bank':off,
                             'opcode_pattern':ABS[op],
                             'status':'raw_literal_not_proven_executed'})
            elif op in INDEXED and buf[off+1]==0x92:
                hits.append({'physical_prg_bank':bank,'offset_in_bank':off,
                             'opcode_pattern':INDEXED[op],
                             'status':'indexed_base_not_actual_target'})
    return hits

def wrap_decrement(value):
    """Branch result at fixed-bank $E50F->$E522, for any unsigned byte."""
    if type(value) is not int or not 0<=value<=255:
        raise ValueError('Expected 8-bit RAM index')
    return ((0x16 if value==0 else value)-1)&255

def wrap_increment(value):
    """Branch result at $E519->$E522; comparison #$15 is unsigned."""
    if type(value) is not int or not 0<=value<=255:
        raise ValueError('Expected 8-bit RAM index')
    return ((value if value<0x15 else 0xff)+1)&255

def inspect(prg):
    anchors=verify(prg)
    hits=direct_write_patterns(prg)
    bybank=[]
    for b in range(16):
        matches=[h for h in hits if h['physical_prg_bank']==b]
        bybank.append({
            'bank':b,
            'direct_literal_patterns':sum(h['status']=='raw_literal_not_proven_executed' for h in matches),
            'indexed_base_patterns':sum(h['status']=='indexed_base_not_actual_target' for h in matches)
        })
    return {
        'schema':1,'prg_sha256':hashlib.sha256(prg).hexdigest(),
        'all_anchors_verified':all(x['signature_verified'] for x in anchors),
        'verified_instruction_anchors':anchors,
        'wraparound_path_domain':'Only seed $15 and wrap paths keep a 0..21 domain',
        'decrement_edge_cases':{str(x):wrap_decrement(x) for x in (0,1,20,21,22,147)},
        'increment_edge_cases':{str(x):wrap_increment(x) for x in (0,1,20,21,22,147)},
        'other_verified_writers':[
            'Bank14 writes constant $93 (147) to RAM $92',
            'Bank14 reads RAM $92 from ($A8),Y with Y=$18; range unproven'],
        'raw_candidate_write_patterns_by_bank':bybank,
        'caveats':[
            'Only one wraparound path is bounded, not all possible RAM $92 assignments',
            'Bank14 physical code has runtime-dependent MMC3 CPU mapping',
            'Byte-pattern hits may be data, unreachable code or indexed base only',
            'No confirmed call graph or first-stage runtime use of the pointer table',
            'No original stage/level geometry or collision information recovered'
        ]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom',type=Path)
    p.add_argument('--out',type=Path,default=Path('private/stage36_index_92_audit.json'))
    args=p.parse_args()
    report=inspect(read_prg(args.rom.read_bytes()))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'verified_anchors':len(report['verified_instruction_anchors']),
                      'wrap_max_in_this_path':21,'globally_bounded':False,
                      'report':str(args.out)},indent=2))

if __name__=='__main__':main()
