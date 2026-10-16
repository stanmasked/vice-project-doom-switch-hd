"""ROM-free invented PRG fragment tests for stage-34 scroll-writer audit."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_scroll_writers import (
    BANK_BYTES,ANCHORS,read_prg,verify_anchors,write_candidates,
    unpack_decoder_byte,inspect)

def fake_prg():
    data=bytearray(16*BANK_BYTES)
    for _,bank,offset,raw,_ in ANCHORS:
        seq=bytes.fromhex(raw)
        data[bank*BANK_BYTES+offset:bank*BANK_BYTES+offset+len(seq)]=seq
    return data

class ScrollWriterTests(unittest.TestCase):
    def test_eight_anchored_fragments(self):
        report=inspect(bytes(fake_prg()))
        self.assertEqual(len(report['checked_anchors']),8)
        self.assertTrue(report['all_anchor_signatures_verified'])
        self.assertEqual([x['physical_prg_bank'] for x in report['checked_anchors']],
                         [15]+[14]*7)
    def test_every_corrupted_anchor_rejected(self):
        for name,bank,off,_,_ in ANCHORS:
            data=fake_prg()
            data[bank*BANK_BYTES+off]^=255
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,name):
                verify_anchors(bytes(data))
            self.assertFalse(all(x['opcode_signature_verified'] for x in
                                 verify_anchors(bytes(data),False)))
    def test_packed_fields_are_transformed(self):
        self.assertEqual(unpack_decoder_byte(0x95),
                         {'ram_0b':0x20,'ram_0c':1,'ram_0d':0x50})
        self.assertEqual(unpack_decoder_byte(0x34),
                         {'ram_0b':0x60,'ram_0c':0,'ram_0d':0x40})
        self.assertEqual(unpack_decoder_byte(0),
                         {'ram_0b':0,'ram_0c':0,'ram_0d':0})
        for value in (-1,256,True):
            with self.assertRaises(ValueError):unpack_decoder_byte(value)
    def test_raw_hits_not_claimed_executed(self):
        data=fake_prg()
        off=2*BANK_BYTES+0xF0
        data[off:off+8]=bytes([0x85,0x0B,0x95,0x0C,0x8D,0x0D,0,0xEA])
        hits=write_candidates(bytes(data))
        cand=[h for h in hits if h['bank']==2 and 0xF0<=h['offset']<=0xF5]
        self.assertTrue(any(h['zp_target']==11 and
            h['certainty']=='direct_address_byte_pattern' for h in cand))
        self.assertTrue(any(h['zp_target']==12 and
            h['certainty']=='indexed_base_only_not_target' for h in cand))
        self.assertTrue(any(h['zp_target']==13 and
            h['operation']=='STA abs' for h in cand))
        self.assertNotIn('executed',cand[0])
    def test_mapper_and_trainer_checks(self):
        prg=bytes(fake_prg())
        h=bytearray(16)
        h[:4]=b'NES\x1a'
        h[4]=8
        h[6]=0x40
        self.assertEqual(read_prg(bytes(h)+prg),prg)
        h[6]=0x44
        self.assertEqual(read_prg(bytes(h)+bytes(512)+prg),prg)
        for invalid in (bytes(16),bytes(h)+prg,bytes(h)+bytes(512)+prg[:123]):
            with self.assertRaises(ValueError):read_prg(invalid)
    def test_cli_on_invented_nes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            h=bytearray(16)
            h[:4]=b'NES\x1a'
            h[4]=8
            h[6]=0x40
            rom=root/'invented.nes'
            rom.write_bytes(bytes(h)+bytes(fake_prg()))
            output=root/'report.json'
            tool=Path(__file__).resolve().parents[1]/'tools/audit_scroll_writers.py'
            proc=subprocess.run([sys.executable,str(tool),str(rom),
                                 '--out',str(output)],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertIn('"all_anchor_signatures_verified": true',output.read_text())

if __name__=='__main__':
    unittest.main()
