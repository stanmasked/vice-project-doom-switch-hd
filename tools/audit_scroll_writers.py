#!/usr/bin/env python3
"""Evidence-gated static trace of writers of PPU scroll-source RAM $0B-$0D.

All generic scan hits may be PRG data, not executed code. The documented
anchors were confirmed against user-owned ROM locally, but do not establish
first-stage camera/world coordinates or game collision geometry.
"""
import argparse
import hashlib
import json
from pathlib import Path

BANK_BYTES=8192
TARGETS=(11,12,13)
ANCHORS=(
 ('fixed_init',15,0x0580,'A9 00 85 0D 85 0B 85 0C',
  'LDA #$00; STA $0D; STA $0B; STA $0C'),
 ('packed_source_decoder',14,0x0906,
  'A0 00 8C 6D 03 84 0C B1 AA A8 29 F0 4A 4A 4A 85 1D F0 03 EE 6D 03 '
  '98 29 F0 0A 26 0C 85 0B 98 29 0F 85 AD 0A 0A 0A 0A 85 0D 60',
  'Indirect byte ($AA),Y transformed into RAM $0C,$0B,$0D'),
 ('subtract_two_16bit',14,0x0BB0,'A5 0B 38 E9 02 85 0B A5 0C E9 00 85 0C',
  'Subtract 2 with borrow from the $0B/$0C pair'),
 ('increase_two_16bit',14,0x0BC6,'A5 0B 18 69 02 85 0B A5 0C 69 00 85 0C',
  'Add 2 with carry to the $0B/$0C pair'),
 ('decrement_0b_with_borrow',14,0x17B7,'A5 0B D0 02 C6 0C C6 0B',
  'Conditional borrow from $0C, decrement $0B'),
 ('increment_0b_with_carry',14,0x17C9,'E6 0B D0 02 E6 0C',
  'Increment $0B, carry into $0C'),
 ('decrement_0d',14,0x1801,'A5 0D F0 E0 C6 0D',
  'Conditionally decrement $0D'),
 ('increment_0d',14,0x180A,'A5 0D C9 C0 B0 D5 E6 0D',
  'Conditionally increment $0D'),
)
DIRECT_ZP={0x85:'STA',0x86:'STX',0x84:'STY',0xE6:'INC',
           0xC6:'DEC',0x06:'ASL',0x46:'LSR',0x26:'ROL',0x66:'ROR'}
INDEXED_ZP={0x95:'STA zp,X',0x94:'STY zp,X',0x96:'STX zp,Y',
            0xF6:'INC zp,X',0xD6:'DEC zp,X',0x16:'ASL zp,X',
            0x56:'LSR zp,X',0x36:'ROL zp,X',0x76:'ROR zp,X'}
DIRECT_ABS={0x8D:'STA',0x8E:'STX',0x8C:'STY',0xEE:'INC',
            0xCE:'DEC',0x0E:'ASL',0x4E:'LSR',0x2E:'ROL',0x6E:'ROR'}

def read_prg(rom):
    if len(rom)<16 or rom[:4]!=b'NES\x1a':
        raise ValueError('Not an NES ROM')
    h=rom[:16]
    mapper=(h[6]>>4)|(h[7]&0xF0)
    if mapper!=4 or h[4]!=8:
        raise ValueError('Expected MMC3 with 128KiB PRG')
    start=16+(512 if h[6]&4 else 0)
    if len(rom)<start+16*BANK_BYTES:
        raise ValueError('Truncated PRG image')
    return rom[start:start+16*BANK_BYTES]

def verify_anchors(prg,strict=True):
    if len(prg)!=16*BANK_BYTES:
        raise ValueError('Expected 128KiB PRG')
    checked=[]
    failures=[]
    for name,bank,off,raw,description in ANCHORS:
        expected=bytes.fromhex(raw)
        found=prg[bank*BANK_BYTES+off:bank*BANK_BYTES+off+len(expected)]
        verified=found==expected
        if not verified:failures.append(name)
        checked.append({'name':name,'physical_prg_bank':bank,
                        'offset_in_bank':off,
                        'cpu_address_if_mmc3_mode0':'$%04X'%((0xE000 if bank==15 else 0xC000)+off),
                        'opcode_signature_verified':verified,
                        'instruction_description':description})
    if failures and strict:
        raise ValueError('ROM writer anchor mismatch: '+', '.join(failures))
    return checked

def write_candidates(prg):
    """Raw byte matches only; never assert reachability or actual target for indexed."""
    if len(prg)!=16*BANK_BYTES:
        raise ValueError('Expected 128KiB PRG')
    hits=[]
    for bank in range(16):
        buf=prg[bank*BANK_BYTES:(bank+1)*BANK_BYTES]
        for off in range(BANK_BYTES-1):
            op=buf[off]
            if op in DIRECT_ZP and buf[off+1] in TARGETS:
                hits.append({'bank':bank,'offset':off,'operation':DIRECT_ZP[op],
                             'zp_target':buf[off+1],
                             'certainty':'direct_address_byte_pattern'})
            elif op in INDEXED_ZP and buf[off+1] in TARGETS:
                hits.append({'bank':bank,'offset':off,'operation':INDEXED_ZP[op],
                             'zp_target':buf[off+1],
                             'certainty':'indexed_base_only_not_target'})
            elif off<BANK_BYTES-2 and op in DIRECT_ABS and buf[off+1] in TARGETS and buf[off+2]==0:
                hits.append({'bank':bank,'offset':off,'operation':DIRECT_ABS[op]+' abs',
                             'zp_target':buf[off+1],
                             'certainty':'direct_address_byte_pattern'})
    return hits

def unpack_decoder_byte(value):
    """Symbolically evaluate the verified decoder for a hypothetical source byte."""
    if type(value) is not int or not 0<=value<=255:
        raise ValueError('Expected 8-bit value')
    return {'ram_0b':((value&0xF0)<<1)&255,
            'ram_0c':(value>>7)&1,
            'ram_0d':(value&15)<<4}

def inspect(prg,strict=True):
    anchors=verify_anchors(prg,strict)
    hits=write_candidates(prg)
    bank_counts=[]
    for bank in range(16):
        candidates=[v for v in hits if v['bank']==bank]
        direct=[v for v in candidates if v['certainty']=='direct_address_byte_pattern']
        bank_counts.append({'physical_prg_bank':bank,
                            'direct_byte_patterns':len(direct),
                            'indexed_base_only_patterns':len(candidates)-len(direct),
                            'direct_targets':{'$%02X'%zp:sum(v['zp_target']==zp for v in direct)
                                              for zp in TARGETS}})
    return {'schema':1,'prg_sha256':hashlib.sha256(prg).hexdigest(),
            'checked_anchors':anchors,
            'all_anchor_signatures_verified':all(v['opcode_signature_verified'] for v in anchors),
            'decoder_example_for_input_0x95':unpack_decoder_byte(0x95),
            'direct_raw_writes':[v for v in hits if v['certainty']=='direct_address_byte_pattern'],
            'counts_by_bank':bank_counts,
            'limits':['Byte matches may contain data and unreachable instructions',
                      'Bank14 CPU mapping $C000-$DFFF is conditional on MMC3 PRG mode 0',
                      'Indirect and indexed absolute stores are not resolved here',
                      'The pointer source ($AA),Y is not yet identified',
                      'No proof of live first-level execution or camera coordinates',
                      'No original collision/metatile/level geometry recovered']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom',type=Path)
    p.add_argument('--out',type=Path,default=Path('private/stage34_scroll_writers.json'))
    p.add_argument('--non-strict',action='store_true')
    args=p.parse_args()
    result=inspect(read_prg(args.rom.read_bytes()),strict=not args.non_strict)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'verified_anchors':result['all_anchor_signatures_verified'],
          'direct_raw_candidates':len(result['direct_raw_writes']),
          'bank14_candidates':result['counts_by_bank'][14]['direct_byte_patterns'],
          'bank15_candidates':result['counts_by_bank'][15]['direct_byte_patterns'],
          'private_report':str(args.out)},indent=2))

if __name__=='__main__':
    main()
