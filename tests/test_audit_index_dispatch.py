"""Invented 6502 test fragments only; never original NES code dumps."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_index_dispatch import (ANCHORS,BANK_SIZE,PRG_BYTES,read_prg,
    verify_anchors,check_edges,branch_destination,input_path,index_update,report)

def invented_prg():
    prg=bytearray(PRG_BYTES)
    for _,pc,raw in ANCHORS:
        b=bytes.fromhex(raw)
        start=15*BANK_SIZE+pc-0xE000
        prg[start:start+len(b)]=b
    return prg

class DispatchAuditTests(unittest.TestCase):
    def test_original_free_anchors_and_destinations(self):
        data=report(bytes(invented_prg()))
        self.assertEqual(len(data['checked_instructions']),9)
        self.assertTrue(data['all_signatures_verified'])
        edges=data['verified_static_edges']
        self.assertEqual(edges['state_13_table_target'],'$E4E6')
        self.assertEqual(edges['nonzero_state_branch_to_input'],'$E4F3')
        self.assertEqual(edges['first_test_branch_to_decrement'],'$E50F')
        self.assertEqual(edges['second_test_branch_to_increment'],'$E519')

    def test_every_changed_instruction_fails(self):
        for name,pc,_ in ANCHORS:
            with self.subTest(name=name):
                p=invented_prg()
                p[15*BANK_SIZE+pc-0xE000]^=255
                with self.assertRaisesRegex(ValueError,name):
                    verify_anchors(bytes(p))
                self.assertFalse(all(x['bytes_verified'] for x in verify_anchors(bytes(p),False)))

    def test_branch_destinations_also_fail_closed(self):
        self.assertEqual(branch_destination(0xE4E8,9),0xE4F3)
        self.assertEqual(branch_destination(0xFFFD,255),0xFFFE)
        p=invented_prg()
        p[15*BANK_SIZE+0xE4F6-0xE000]=8
        with self.assertRaisesRegex(ValueError,'Control-flow destinations'):
            check_edges(bytes(p))

    def test_bit_priority_and_gate(self):
        self.assertEqual(input_path(0x04),'decrement_index')
        self.assertEqual(input_path(0x08),'increment_index')
        self.assertEqual(input_path(0x0c),'decrement_index')
        self.assertEqual(input_path(0x80),'special_state_11')
        self.assertEqual(input_path(0x8c),'special_state_11')
        self.assertEqual(input_path(0),'return_no_index_change')
        self.assertEqual(input_path(0x0c,0),'initialization_refresh_no_input_test')
        for bad in (-1,256,True):
            with self.assertRaises(ValueError):input_path(bad)

    def test_index_edges_no_fake_global_clamping(self):
        self.assertEqual(index_update(0,'decrement_index'),21)
        self.assertEqual(index_update(21,'increment_index'),0)
        self.assertEqual(index_update(147,'decrement_index'),146)
        self.assertEqual(index_update(147,'increment_index'),0)
        self.assertIsNone(index_update(5,'special_state_11'))
        self.assertEqual(index_update(5,'return_no_index_change'),5)
        for bad in (-1,256,True):
            with self.assertRaises(ValueError):index_update(bad,'decrement_index')

    def test_ines_and_trainer(self):
        h=bytearray(16);h[:4]=b'NES\x1a';h[4]=8;h[6]=0x40
        prg=bytes(invented_prg())
        self.assertEqual(read_prg(bytes(h)+prg),prg)
        h[6]=0x44
        self.assertEqual(read_prg(bytes(h)+bytes(512)+prg),prg)
        with self.assertRaises(ValueError):read_prg(bytes(h)+prg)
        with self.assertRaises(ValueError):read_prg(b'garbage')

    def test_synthetic_commandline_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            h=bytearray(16);h[:4]=b'NES\x1a';h[4]=8;h[6]=0x40
            rom=root/'invented.nes'
            rom.write_bytes(bytes(h)+bytes(invented_prg()))
            out=root/'audit.json'
            script=Path(__file__).resolve().parents[1]/'tools/audit_index_dispatch.py'
            proc=subprocess.run([sys.executable,str(script),str(rom),'--out',str(out)],
                                capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertEqual(len(json.loads(out.read_text())['verified_static_edges']),7)

if __name__=='__main__':unittest.main()
