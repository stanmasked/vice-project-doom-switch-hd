#!/usr/bin/env python3
"""Strict static audit of possible PRG-bank-12 $AA/$AB table-pointer setup.

All offsets are physical 8KiB PRG bank offsets. This only confirms opcode
anchors, not execution in the first level or camera/collision semantics.
Keep original ROM, table bytes and full local reports outside GitHub.
"""
import argparse
import hashlib
import json
from pathlib import Path

BANK_SIZE=8192
PRG_SIZE=16*BANK_SIZE
ANCHORS=(
    ('pointer_table_lookup',12,0x035B,
     'A5 92 0A 65 92 69 76 85 AA A9 00 69 83 85 AB A0 01 B1 AA 85 A8 C8 B1 AA 85 A9 60'),
    ('consumer_decoder_start',14,0x0906,
     'A0 00 8C 6D 03 84 0C B1 AA A8 29 F0'),
    ('consumer_direct_call',14,0x08CA,'20 06 C9'),
)
DIRECT_WRITES={0x85:'STA zp',0x86:'STX zp',0x84:'STY zp',
               0xE6:'INC zp',0xC6:'DEC zp',0x06:'ASL zp',
               0x46:'LSR zp',0x26:'ROL zp',0x66:'ROR zp'}

def read_prg(rom):
    if len(rom)<16 or rom[:4]!=b'NES\x1a':
        raise ValueError('Expected NES file')
    h=rom[:16]
    if (h[6]>>4)|(h[7]&0xf0)!=4 or h[4]!=8:
        raise ValueError('Expected MMC3 and 128KiB PRG')
    start=16+(512 if h[6]&4 else 0)
    if len(rom)<start+PRG_SIZE:
        raise ValueError('Truncated PRG')
    return rom[start:start+PRG_SIZE]

def verify(prg,strict=True):
    if len(prg)!=PRG_SIZE:raise ValueError('Expected 128KiB PRG')
    records=[]
    failures=[]
    for name,bank,off,signature in ANCHORS:
        raw=bytes.fromhex(signature)
        good=prg[bank*BANK_SIZE+off:bank*BANK_SIZE+off+len(raw)]==raw
        records.append({'name':name,'physical_prg_bank':bank,
                        'offset_in_8k_bank':off,'signature_verified':good})
        if not good:failures.append(name)
    if failures and strict:raise ValueError('Instruction mismatch: '+', '.join(failures))
    return records

def pointer_emulation(index):
    """Emulate exact ASL+ADC+ADC carry, NOT assumed unlimited base+3*i."""
    if type(index) is not int or not 0<=index<=255:
        raise ValueError('Index must be an unsigned byte')
    a=(index*2)&255
    carry=index>>7
    result=a+index+carry
    a,carry=result&255,result>>8
    result=a+0x76+carry
    low,carry=result&255,result>>8
    high=(0x83+carry)&255
    return (high<<8)|low

def direct_candidate_writers(prg):
    """Literal byte patterns. Could be data or unreached 6502 instructions."""
    if len(prg)!=PRG_SIZE:raise ValueError('Expected 128KiB PRG')
    hits=[]
    for bank in range(16):
        buf=prg[bank*BANK_SIZE:(bank+1)*BANK_SIZE]
        for off in range(BANK_SIZE-1):
            op=buf[off]
            if op in DIRECT_WRITES and buf[off+1] in (0xAA,0xAB):
                hits.append({'bank':bank,'offset':off,
                             'target':'$%02X'%buf[off+1],
                             'raw_instruction_pattern':DIRECT_WRITES[op],
                             'confidence':'byte_pattern_not_proven_executed'})
    return hits

def inspect(prg):
    anchors=verify(prg)
    hits=direct_candidate_writers(prg)
    mapping=[]
    for idx in (0,1,2,10,40,46,85,86):
        ptr=pointer_emulation(idx)
        mapping.append({'hypothetical_ram_92':idx,
                        'computed_cpu_pointer':'$%04X'%ptr,
                        'matches_base_plus_3index':ptr==(0x8376+idx*3),
                        'table_offset_if_bank12_at_8000':ptr-0x8000
                          if 0x8000<=ptr<0xA000 else None})
    return {
        'schema':1,'prg_sha256':hashlib.sha256(prg).hexdigest(),
        'anchor_status':anchors,'all_anchors_verified':True,
        'statically_observed_relationships':[
            'Bank12 $035B uses RAM $92 and computes pointer $AA/$AB',
            'Bank12 reads descriptor bytes 1 and 2 via ($AA),Y into $A8/$A9',
            'Bank14 decoder reads byte 0 via ($AA),Y',
            'Bank14 contains JSR $C906 in conditional mode-0 CPU mapping',
            'Table base $8376 requires bank12 mapped into CPU $8000 slot'],
        'hypothetical_index_examples':mapping,
        'raw_direct_aa_ab_writer_candidates':hits,
        'caveats':[
            'No proven runtime path from bank12 setup to bank14 decoder',
            'No verified first-stage identity or valid range for RAM $92',
            'ASL/ADC carry differs from ordinary base+3*i for some indices including 86',
            'MMC3 mode and $8000 bank must be verified dynamically',
            'Raw byte matches may be nonexecuted code or data',
            'No authentic world camera, metatiles or collision map recovered']}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom',type=Path)
    p.add_argument('--out',type=Path,default=Path('private/stage35_pointer_trace.json'))
    args=p.parse_args()
    result=inspect(read_prg(args.rom.read_bytes()))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'anchors_verified':result['all_anchors_verified'],
       'direct_aa_ab_raw_candidates':len(result['raw_direct_aa_ab_writer_candidates']),
       'private_report':str(args.out),
       'warning':'Static candidate link, not proven runtime stage/camera'},indent=2))
if __name__=='__main__':main()
