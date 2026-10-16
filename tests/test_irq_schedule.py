"""ROM-free synthetic fixtures for IRQ schedule analysis."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from inspect_irq_schedule import (ANCHORS, START, END, WIDTH, extract_rows,
                                  validate_anchors, inspect, last_bank)

def fake_rom_bank():
    bank=bytearray(8192)
    for n,addr in enumerate(range(START,END,WIDTH)):
        bank[addr-0xE000:addr-0xE000+5]=bytes([0x91,0xE3,n,n%4,n%8])
    for addr,hexdump in ANCHORS.items():
        seq=bytes.fromhex(hexdump)
        bank[addr-0xE000:addr-0xE000+len(seq)]=seq
    bank[0xE391-0xE000]=0x60  # synthetic RTS
    bank[-2:]=(0xE1DA).to_bytes(2,'little')
    return bytes(bank)

class IrqScheduleTests(unittest.TestCase):
    def test_rows(self):
        rows=extract_rows(fake_rom_bank())
        self.assertEqual(len(rows),41)
        self.assertEqual(rows[0]['cpu_address'],'0xE10D')
        self.assertEqual(rows[40]['cpu_address'],'0xE1D5')
        self.assertEqual(rows[40]['mmc3_irq_latch'],40)
        self.assertEqual(rows[5]['ram_0033'],1)
    def test_all_anchors(self):
        bank=fake_rom_bank()
        self.assertFalse(validate_anchors(bank))
        result=inspect(bytes(8192)+bank,strict=True)
        self.assertEqual(result['unique_handlers'],1)
        self.assertEqual(result['row_count'],41)
        self.assertEqual(result['validated_instruction_anchors'],20)
        self.assertFalse(result['undecodable_handler_indices'])
    def test_modified_instruction_fails(self):
        bank=bytearray(fake_rom_bank())
        bank[0xE0C4-0xE000]=0
        self.assertTrue(validate_anchors(bank))
        with self.assertRaisesRegex(ValueError,'anchor mismatch'):
            inspect(bank,strict=True)
    def test_bad_boundaries(self):
        with self.assertRaises(ValueError):
            extract_rows(bytes(8192),end=END-1)
        with self.assertRaises(ValueError):
            extract_rows(bytes(8191))
        with self.assertRaises(ValueError):
            last_bank(bytes(20))
    def test_transition_graph(self):
        from inspect_irq_schedule import transition_graph
        graph=transition_graph(extract_rows(fake_rom_bank()))
        self.assertEqual(graph['zero_indegree'],list(range(4,41)))
        self.assertEqual(graph['cycles'],[[0],[1],[2],[3]])
    def test_handler_opcode(self):
        bank=bytearray(fake_rom_bank())
        bank[0xE391-0xE000]=0x02 # unsupported opcode
        with self.assertRaisesRegex(ValueError,'Invalid handler'):
            inspect(bank,strict=True)

if __name__=='__main__':
    unittest.main()
