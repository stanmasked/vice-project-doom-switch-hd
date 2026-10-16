#!/usr/bin/env python3
"""Decode the Vice NES NMI $0600 queue into semantic PPU operations.

No PPU, CPU, bank mapper or game simulation. Bytes read from the owner's
ROM or memory dumps must remain local. Static handler findings are
revision-specific and verified via code instruction anchors.
"""
import argparse
import json
from pathlib import Path

from disassemble_fixed_bank import decode
from inspect_rom import parse_rom
from inspect_ppu_queue import inspect as inspect_dispatcher

PACKET_PAYLOAD_LENGTH = {1: 7, 2: 0, 3: 0, 4: 3, 5: 12, 6: 7, 7: 4, 8: 4}
# These facts are instruction addresses, not copied ROM code or data.
HANDLER_ANCHORS = {
    0xE62D: 'INY',
    0xE631: 'LDA $0600,Y',
    0xE63A: 'STA $2006',
    0xE646: 'STA $2007',
    0xE64E: 'JSR $DFC6',
    0xE655: 'STA $2000',
    0xE67B: 'STY $16',
    0xE680: 'LDA ($02),Y',
    0xE690: 'INY',
    0xE69D: 'LDA #$3F',
    0xE6A5: 'LDA $0140,X',
    0xE6FF: 'LDA $014F,X',
    0xE705: 'RTS',
    0xE706: 'INY',
    0xE72B: 'STA $2007',
    0xE74A: 'STA $2007',
    0xE74D: 'INY',
    0xE767: 'AND $0600,Y',
    0xE76B: 'ORA $0600,Y',
    0xE77E: 'STY $16',
    0xE781: 'INY',
    0xE78F: 'LDA #$08',
    0xE7A3: 'AND $0600,Y',
    0xE7A7: 'ORA $0600,Y',
    0xE7BA: 'INC $03',
    0xE7BC: 'DEC $04',
    0xE7BE: 'BNE $E793',
    0xE7C0: 'STY $16',
}

def validate_handlers(prg):
    if len(prg) < 8192 or len(prg) % 8192:
        raise ValueError('PRG is not 8KiB aligned')
    bank = prg[-8192:]
    mismatches = []
    for pc, expected in HANDLER_ANCHORS.items():
        ins = decode(bank, pc)
        if ins is None or ins['asm'] != expected:
            mismatches.append('0x%04X' % pc)
    if mismatches:
        raise ValueError('Handler instruction mismatch: ' + ', '.join(mismatches))
    return len(HANDLER_ANCHORS)

def _ppu_addr(low, high):
    return ((high << 8) | low) & 0x3fff

def _cpu_data(cpu_snapshot, source, length):
    if cpu_snapshot is None:
        return None
    if len(cpu_snapshot) != 65536:
        raise ValueError('CPU snapshot must be 65536 bytes')
    return [cpu_snapshot[(source + i) & 0xffff] for i in range(length)]

def _packet(queue, index, cpu_snapshot):
    command = queue[index]
    if command not in PACKET_PAYLOAD_LENGTH:
        raise ValueError('Unknown PPU queue command %d at index %d' % (command, index))
    count = PACKET_PAYLOAD_LENGTH[command]
    end = index + 1 + count
    if end > len(queue) or end > 256:
        raise ValueError('Truncated queue packet at index %d' % index)
    p = queue[index+1:end]
    ops = []
    if command in (1, 6):
        # The JSR at $E64E may change mapped PRG banks before source reads.
        source = (p[5] << 8) | p[4]
        n = p[6] or 256  # LDX #$00 then DEX/BNE copies 256 bytes.
        ops.append({
            'kind': 'cpu_to_ppu_copy', 'ppu_ctrl': p[1],
            'ppu_address': _ppu_addr(p[2], p[3]),
            'bank_argument': p[0], 'cpu_source': source, 'length': n,
            'requires_post_bank_switch_snapshot': True
        })
    elif command in (2, 3):
        half = 0 if command == 3 else 16  # #3 starts X=$10; #2 X=$00
        source = 0x140 + half
        op = {'kind': 'palette_upload', 'ppu_address': 0x3f00 + half,
              'cpu_source': source, 'length': 16}
        values = _cpu_data(cpu_snapshot, source, 16)
        if values is not None:
            op['data'] = values
        ops.append(op)
    elif command == 4:
        ops.append({'kind':'ppu_write','ppu_address':_ppu_addr(p[0],p[1]),
                    'data':[p[2]]})
    elif command == 5:
        ops.append({'kind':'ppu_write','ppu_address':_ppu_addr(p[0],p[1]),
                    'data':[p[2],p[3]]})
        ops.append({'kind':'ppu_write','ppu_address':_ppu_addr(p[4],p[5]),
                    'data':[p[6],p[7]]})
        # $E74A falls through to $E74D (the #7 masked-write handler).
        ops.append({'kind':'ppu_masked_write',
                    'ppu_address':_ppu_addr(p[8],p[9]),
                    'and_mask':p[10],'or_mask':p[11],'count':1})
    elif command == 7:
        ops.append({'kind':'ppu_masked_write',
                    'ppu_address':_ppu_addr(p[0],p[1]),
                    'and_mask':p[2],'or_mask':p[3],'count':1})
    elif command == 8:
        ops.append({'kind':'ppu_masked_write',
                    'ppu_address':_ppu_addr(p[0],p[1]),
                    'and_mask':p[2],'or_mask':p[3],'count':8,
                    'wrap_low_address_byte':True})
    return {'command':command,'start_index':index,'next_index':end,'operations':ops}

def decode_queue(queue, costs=None, frame_budget=60, start_index=0, cpu_snapshot=None):
    """Decode at most one NMI service pass; stops on terminator or low budget.

    No PPU state is altered. Masked read/modify/write operations are left
    symbolic because PPU read buffering and mirroring are not simulated.
    """
    if not isinstance(queue, (bytes, bytearray)) or len(queue) > 256:
        raise ValueError('Queue must be at most 256 bytes')
    if not 0 <= start_index <= len(queue):
        raise ValueError('Invalid queue index')
    if costs is not None and (len(costs)!=8 or any(not 0<=c<=255 for c in costs)):
        raise ValueError('Exactly eight byte-sized command costs required')
    if not 0 <= frame_budget <= 255:
        raise ValueError('Budget must be one byte')
    if cpu_snapshot is not None and len(cpu_snapshot)!=65536:
        raise ValueError('CPU snapshot must be 65536 bytes')
    index=start_index
    remaining=frame_budget
    packets=[]
    halt='end_of_buffer'
    while index < len(queue):
        command=queue[index]
        if command == 0:
            halt='terminator'
            break
        if command not in PACKET_PAYLOAD_LENGTH:
            raise ValueError('Unknown command %d at index %d' % (command,index))
        cost = costs[command-1] if costs is not None else None
        if cost is not None and remaining < cost:
            halt='budget_exhausted'
            break
        packet=_packet(queue,index,cpu_snapshot)
        if cost is not None:
            packet['cost_units']=cost
            remaining -= cost
        packets.append(packet)
        index=packet['next_index']
    return {'start_index':start_index, 'next_index':index,
            'initial_budget':frame_budget if costs is not None else None,
            'remaining_budget':remaining if costs is not None else None,
            'halt_reason':halt, 'packets':packets,
            'caveats':['Synthetic or captured RAM bytes only, never a substitute for dynamic PPU trace',
                       'CPU-copy source data may change after bank-switch call',
                       'Masked PPU operations are symbolic; PPU read-buffer timing is not simulated']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom',help='Owned NES ROM for handler/cost verification')
    p.add_argument('queue',help='Local raw memory capture of RAM $0600-$06FF')
    p.add_argument('--cpu-snapshot',help='Optional full 64KiB CPU memory snapshot')
    p.add_argument('--index',type=lambda s:int(s,0),default=0)
    p.add_argument('--out',help='Private local JSON report, not for Git')
    args=p.parse_args()
    rom=parse_rom(args.rom)
    if rom['mapper'] != 4:
        p.error('Expected mapper 4 MMC3')
    validated=validate_handlers(rom['prg'])
    metadata=inspect_dispatcher(rom['prg'],strict=True)
    costs=[c['budget_units'] for c in metadata['commands']]
    q=Path(args.queue).read_bytes()
    cpu=Path(args.cpu_snapshot).read_bytes() if args.cpu_snapshot else None
    result=decode_queue(q,costs=costs,start_index=args.index,cpu_snapshot=cpu)
    result['validated_handler_anchors']=validated
    out=json.dumps(result,indent=2)+'\n'
    if args.out:
        path=Path(args.out)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(out,encoding='utf8')
    print(out,end='')

if __name__ == '__main__':
    main()
