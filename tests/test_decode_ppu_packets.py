"""Synthetic ROM-free PPU packet regression tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from decode_ppu_packets import _packet, decode_queue, validate_handlers, PACKET_PAYLOAD_LENGTH, HANDLER_ANCHORS
from disassemble_fixed_bank import SPECS

def packet(cmd, *data):
    assert len(data) == PACKET_PAYLOAD_LENGTH[cmd]
    return bytes([cmd,*data])

class PpuPacketTests(unittest.TestCase):
    def test_single_write_and_index(self):
        r=decode_queue(packet(4,0x20,0x3f,0x9e)+b'\x00')
        self.assertEqual(r['halt_reason'],'terminator')
        self.assertEqual(r['next_index'],4)
        self.assertEqual(r['packets'][0]['operations'],
             [{'kind':'ppu_write','ppu_address':0x3f20,'data':[0x9e]}])

    def test_palette_halves_and_real_ram_snapshot(self):
        cpu=bytearray(65536)
        cpu[0x140:0x160]=bytes(range(32))
        r=decode_queue(packet(2)+packet(3)+b'\x00',cpu_snapshot=cpu)
        a,b=[p['operations'][0] for p in r['packets']]
        self.assertEqual(a['ppu_address'],0x3f00)
        self.assertEqual(b['ppu_address'],0x3f10)
        self.assertEqual(a['data'],list(range(16)))
        self.assertEqual(b['data'],list(range(16,32)))

    def test_both_cpu_copies_and_zero_means_256(self):
        one=packet(1,0x7c,0x04,0x0a,0x20,0x34,0x12,0)
        two=packet(6,0x7d,0x05,0x10,0x24,0x45,0x23,0x0e)
        a,b=decode_queue(one+two+b'\x00')['packets']
        self.assertEqual(a['operations'][0]['length'],256)
        self.assertEqual(b['operations'][0]['length'],14)
        self.assertEqual(a['operations'][0]['cpu_source'],0x1234)
        self.assertEqual(a['operations'][0]['ppu_address'],0x200a)
        self.assertTrue(a['operations'][0]['requires_post_bank_switch_snapshot'])

    def test_command5_falls_through_to_masked_write(self):
        command=packet(5,0x00,0x20,0x12,0x34,0x08,0x20,0x56,0x78,0x10,0x23,0xf0,0x03)
        r=decode_queue(command+b'\x00')
        self.assertEqual(r['next_index'],13)
        self.assertEqual(r['packets'][0]['operations'],[
            {'kind':'ppu_write','ppu_address':0x2000,'data':[0x12,0x34]},
            {'kind':'ppu_write','ppu_address':0x2008,'data':[0x56,0x78]},
            {'kind':'ppu_masked_write','ppu_address':0x2310,'and_mask':0xf0,
             'or_mask':3,'count':1}
        ])

    def test_masked_single_and_eight(self):
        q=packet(7,0x00,0x24,0xfe,0x01)+packet(8,0xfe,0x23,0x0f,0xe0)+b'\x00'
        a,b=[p['operations'][0] for p in decode_queue(q)['packets']]
        self.assertEqual(a['count'],1)
        self.assertEqual(b['count'],8)
        self.assertTrue(b['wrap_low_address_byte'])
        self.assertEqual(b['ppu_address'],0x23fe)

    def test_frame_budget_stops_before_command(self):
        q=packet(4,0x00,0x20,1)+packet(4,0x01,0x20,2)+b'\x00'
        r=decode_queue(q,costs=[1,1,1,4,1,1,1,1],frame_budget=6)
        self.assertEqual(len(r['packets']),1)
        self.assertEqual(r['remaining_budget'],2)
        self.assertEqual(r['next_index'],4)
        self.assertEqual(r['halt_reason'],'budget_exhausted')

    def test_truncated_and_invalid(self):
        with self.assertRaisesRegex(ValueError,'Truncated'):
            decode_queue(bytes([5,0x00]))
        with self.assertRaisesRegex(ValueError,'Unknown'):
            decode_queue(bytes([9]))
        with self.assertRaisesRegex(ValueError,'CPU snapshot'):
            decode_queue(bytes([2,0]),cpu_snapshot=bytes(64))
        with self.assertRaisesRegex(ValueError,'eight'):
            decode_queue(bytes([0]),costs=[1,2])
        with self.assertRaises(ValueError):
            decode_queue(bytes(257))
        self.assertEqual(decode_queue(bytes([4,0,0,0]*64))['halt_reason'],'end_of_buffer')

    def test_handler_anchors_on_invented_6502(self):
        # Synthetic instruction encoding for enough supported anchors;
        # no original commercial machine code is stored in the test.
        by_op={(name,mode):op for name,modes in SPECS.items() for mode,op in modes.items()}
        b=bytearray([0xea]*8192)
        for pc,expected in HANDLER_ANCHORS.items():
            op, *arg=expected.split(' ')
            if not arg:
                mode='imp'; raw=[]
            elif arg[0]=='A':
                mode='acc'; raw=[]
            elif arg[0].startswith('#'):
                mode='imm'; raw=[int(arg[0][2:],16)]
            else:
                value=int(arg[0].split(',')[0].replace('
                mode=('rel' if op.startswith('B') else
                    'indy' if arg[0].startswith('(') else
                    'absx' if arg[0].endswith(',X') and value>255 else
                    'absy' if arg[0].endswith(',Y') and value>255 else
                    'zp' if value<=255 else 'abs')
                if mode=='rel':
                    raw=[(value-(pc+2))&255]
                elif mode=='indy':
                    raw=[value]
                elif mode=='zp':
                    raw=[value]
                else:
                    raw=[value&255,value>>8]
            try: opcode=by_op[(op,mode)]
            except KeyError as e: raise AssertionError((pc,expected,mode)) from e
            b[pc-0xe000:pc-0xe000+1+len(raw)]=bytes([opcode,*raw])
        self.assertEqual(validate_handlers(b),len(HANDLER_ANCHORS))
        b[0xe74d-0xe000]=0
        with self.assertRaisesRegex(ValueError,'Handler instruction mismatch'):
            validate_handlers(bytes(b))

if __name__=='__main__':unittest.main()
,'').replace('(','').replace(')',''),16)
                mode=('rel' if op.startswith('B') else
                    'indy' if arg[0].startswith('(') else
                    'absx' if arg[0].endswith(',X') and value>255 else
                    'absy' if arg[0].endswith(',Y') and value>255 else
                    'zp' if value<=255 else 'abs')
                if mode=='rel':
                    raw=[(value-(pc+2))&255]
                elif mode=='indy':
                    raw=[value]
                elif mode=='zp':
                    raw=[value]
                else:
                    raw=[value&255,value>>8]
            try: opcode=by_op[(op,mode)]
            except KeyError as e: raise AssertionError((pc,expected,mode)) from e
            b[pc-0xe000:pc-0xe000+1+len(raw)]=bytes([opcode,*raw])
        self.assertEqual(validate_handlers(b),len(HANDLER_ANCHORS))
        b[0xe74d-0xe000]=0
        with self.assertRaisesRegex(ValueError,'Handler instruction mismatch'):
            validate_handlers(bytes(b))

if __name__=='__main__':unittest.main()
