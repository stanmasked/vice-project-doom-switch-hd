#!/usr/bin/env python3
"""Conservative ROM-local 6502 branch audit for the RAM-$92 state path.

Anchored instructions and branch destinations are static evidence only.
They do not prove first-stage runtime execution, camera state, or collision.
Do not upload original ROMs, extracted tiles, or private capture files.
"""
import argparse
import hashlib
import json
from pathlib import Path

BANK_SIZE=8192
PRG_BYTES=16*BANK_SIZE
FIXED_BASE=0xE000
ANCHORS=(
 ('index_seed_and_external_call',0xE418,'A9 15 85 92 20 47 C1'),
 ('state_dispatch',0xE479,'A5 90 0A AA BD A6 E4 85 25 BD A7 E4 85 26 6C 25 00'),
 ('dispatch_table_state_13',0xE4C0,'E6 E4'),
 ('state_gate',0xE4E6,'A5 91 D0 09 20 77 E5 20 22 E5 E6 91 60'),
 ('input_priority_branch',0xE4F3,'A5 07 30 09 4A 4A 4A B0 13 4A B0 1A 60'),
 ('special_input_path',0xE500,'A9 0B 85 90 A9 00 85 91 A9 01 A2 00 4C DB D6'),
 ('index_decrement',0xE50F,'A6 92 D0 02 A2 16 CA 4C 22 E5'),
 ('index_increment',0xE519,'A6 92 E0 15 90 02 A2 FF E8'),
 ('common_index_store',0xE522,'86 92 8A A2 0F 86 1D A2 0E 86 1E 4C 53 E5'),
)

def read_prg(data):
    if len(data)<16 or data[:4]!=b'NES\x1a':
        raise ValueError('Not an NES ROM')
    h=data[:16]
    mapper=(h[6]>>4)|(h[7]&0xf0)
    offset=16+(512 if h[6]&4 else 0)
    if mapper!=4 or h[4]!=8 or len(data)<offset+PRG_BYTES:
        raise ValueError('Expected complete MMC3 128KiB PRG')
    return data[offset:offset+PRG_BYTES]

def verify_anchors(prg,strict=True):
    if len(prg)!=PRG_BYTES:raise ValueError('Expected 128KiB PRG')
    fixed=prg[-BANK_SIZE:]
    rows=[]
    failures=[]
    for name,pc,hexbytes in ANCHORS:
        expected=bytes.fromhex(hexbytes)
        ok=fixed[pc-FIXED_BASE:pc-FIXED_BASE+len(expected)]==expected
        rows.append({'name':name,'cpu_address':'$%04X'%pc,'bytes_verified':ok})
        if not ok:failures.append(name)
    if strict and failures:
        raise ValueError('Changed 6502 anchors: '+', '.join(failures))
    return rows

def branch_destination(pc,relative):
    if not 0<=pc<=65535 or not 0<=relative<=255:
        raise ValueError('Invalid branch operand')
    signed=relative if relative<128 else relative-256
    return (pc+2+signed)&65535

def check_edges(prg):
    if len(prg)!=PRG_BYTES:raise ValueError('Expected 128KiB PRG')
    fixed=prg[-BANK_SIZE:]
    at=lambda pc:fixed[pc-FIXED_BASE]
    actual={
      'nonzero_state_branch_to_input':branch_destination(0xE4E8,at(0xE4E9)),
      'negative_input_branch_to_special':branch_destination(0xE4F5,at(0xE4F6)),
      'first_test_branch_to_decrement':branch_destination(0xE4FA,at(0xE4FB)),
      'second_test_branch_to_increment':branch_destination(0xE4FD,at(0xE4FE)),
      'decrement_zero_branch':branch_destination(0xE511,at(0xE512)),
      'increment_below_21_branch':branch_destination(0xE51D,at(0xE51E)),
      'state_13_table_target':fixed[0x4C0]|(fixed[0x4C1]<<8)
    }
    expected={
      'nonzero_state_branch_to_input':0xE4F3,
      'negative_input_branch_to_special':0xE500,
      'first_test_branch_to_decrement':0xE50F,
      'second_test_branch_to_increment':0xE519,
      'decrement_zero_branch':0xE515,
      'increment_below_21_branch':0xE521,
      'state_13_table_target':0xE4E6}
    if actual!=expected:
        raise ValueError('Control-flow destinations changed: '+repr(actual))
    return {k:'$%04X'%v for k,v in actual.items()}

def input_path(value,state_gate=1):
    """Symbolic conditional routing; no physical button labels are inferred."""
    if type(value) is not int or not 0<=value<=255 or type(state_gate) is not int or not 0<=state_gate<=255:
        raise ValueError('Expected 8-bit RAM values')
    if state_gate==0:return 'initialization_refresh_no_input_test'
    if value&0x80:return 'special_state_11'
    if value&0x04:return 'decrement_index'
    if value&0x08:return 'increment_index'
    return 'return_no_index_change'

def index_update(index,action):
    if type(index) is not int or not 0<=index<=255:
        raise ValueError('Expected byte index')
    if action=='decrement_index':return (21 if index==0 else index-1)&255
    if action=='increment_index':return (index+1 if index<21 else 0)&255
    if action in ('return_no_index_change','initialization_refresh_no_input_test'):
        return index
    if action=='special_state_11':return None
    raise ValueError('Unknown action')

def report(prg):
    anchored=verify_anchors(prg)
    edges=check_edges(prg)
    cases=[]
    for sample in (0,0x04,0x08,0x0C,0x80,0x84,0x88):
        path=input_path(sample)
        cases.append({'synthetic_ram_07':'$%02X'%sample,
                      'gate_ram_91':1,'path':path,
                      'sample_index_0_output':index_update(0,path)})
    return {
        'schema':1,'prg_sha256':hashlib.sha256(prg).hexdigest(),
        'checked_instructions':anchored,
        'all_signatures_verified':all(x['bytes_verified'] for x in anchored),
        'verified_static_edges':edges,
        'state_dispatch_note':'RAM $90=13 indexes word 13 of table $E4A6, pointing to $E4E6; other gates unverified',
        'input_bit_priority':[
            'RAM $91=0 chooses initial refresh before input routing',
            'RAM $07 bit 7 chooses special state first',
            'then bit 2 chooses decrement even when bit 3 is also set',
            'then bit 3 chooses increment, else returns'],
        'synthetic_branch_matrix':cases,
        'caveats':[
            'Static edges do not prove actual first-level execution or frequency',
            'RAM $07 bits have no established physical controller meaning here',
            'JSR $C147 at $E41C requires active MMC3 bank mapping to identify callee',
            'No global domain for RAM $92 is proven by this path',
            'No authentic first-stage camera, collision or map decoded']}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom',type=Path)
    p.add_argument('--out',type=Path,default=Path('private/stage37_dispatch_audit.json'))
    a=p.parse_args()
    data=report(read_prg(a.rom.read_bytes()))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'verified_anchors':len(data['checked_instructions']),
                      'verified_static_edges':len(data['verified_static_edges']),
                      'report':str(a.out),'runtime_proven':False},indent=2))

if __name__=='__main__':main()
