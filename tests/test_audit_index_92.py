"""Synthetic MMC3 code fragments only; no real game PRG bytes in fixtures."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_index_92 import (ANCHORS,BANK,PRG_BYTES,read_prg,verify,
                            direct_write_patterns,wrap_decrement,wrap_increment,inspect)

def fabricated_prg():
    data=bytearray(PRG_BYTES)
    for _,bank,offset,hexbytes,_ in ANCHORS:
        raw=bytes.fromhex(hexbytes)
        data[bank*BANK+offset:bank*BANK+offset+len(raw)]=raw
    return data

class Index92Tests(unittest.TestCase):
    def test_six_verified_anchors(self):
        report=inspect(bytes(fabricated_prg()))
        self.assertEqual(len(report['verified_instruction_anchors']),6)
        self.assertTrue(report['all_anchors_verified'])
        self.assertEqual([x['physical_prg_bank'] for x in report['verified_instruction_anchors']],
                         [15,15,15,14,14,12])

    def test_each_modified_signature_fails_closed(self):
        for name,bank,offset,_,_ in ANCHORS:
            changed=fabricated_prg()
            changed[bank*BANK+offset]^=0xff
            with self.subTest(anchor=name),self.assertRaisesRegex(ValueError,name):
                verify(bytes(changed))
            self.assertFalse(all(x['signature_verified'] for x in verify(bytes(changed),False)))

    def test_wrapped_decrement_and_increment_0_to_21(self):
        self.assertEqual(wrap_decrement(0),21)
        self.assertEqual(wrap_increment(21),0)
        for i in range(1,22):self.assertEqual(wrap_decrement(i),i-1)
        for i in range(21):self.assertEqual(wrap_increment(i),i+1)
        self.assertEqual({wrap_increment(i) for i in range(22)},set(range(22)))
        self.assertEqual({wrap_decrement(i) for i in range(22)},set(range(22)))

    def test_outside_domain_is_not_artificially_clamped(self):
        self.assertEqual(wrap_decrement(147),146)
        self.assertEqual(wrap_increment(147),0)
        self.assertEqual(wrap_decrement(22),21)
        self.assertEqual(wrap_increment(22),0)
        for fn in (wrap_decrement,wrap_increment):
            for bad in (-1,256,True,1.25):
                with self.assertRaises(ValueError):fn(bad)

    def test_raw_pattern_classifier_reports_indexed_uncertainty(self):
        b=fabricated_prg()
        off=2*BANK+314
        b[off:off+8]=bytes([0x85,0x92,0x95,0x92,0x8D,0x92,0,0xea])
        hits=direct_write_patterns(bytes(b))
        subset=[h for h in hits if h['physical_prg_bank']==2 and 314<=h['offset_in_bank']<=320]
        self.assertTrue(any(x['status']=='raw_literal_not_proven_executed' for x in subset))
        self.assertTrue(any(x['status']=='indexed_base_not_actual_target' for x in subset))
        self.assertNotIn('executed',subset[0])

    def test_mapper_header_and_trainer(self):
        h=bytearray(16);h[:4]=b'NES\x1a';h[4]=8;h[6]=0x40
        prg=bytes(fabricated_prg())
        self.assertEqual(read_prg(bytes(h)+prg),prg)
        h[6]=0x44
        self.assertEqual(read_prg(bytes(h)+bytes(512)+prg),prg)
        for bad in (b'x'*16, bytes(h)+prg, bytes(h)+bytes(512)+prg[:120]):
            with self.assertRaises(ValueError):read_prg(bad)

    def test_synthetic_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            h=bytearray(16);h[:4]=b'NES\x1a';h[4]=8;h[6]=0x40
            rom=root/'invented.nes';rom.write_bytes(bytes(h)+bytes(fabricated_prg()))
            out=root/'audit.json'
            script=Path(__file__).resolve().parents[1]/'tools/audit_index_92.py'
            process=subprocess.run([sys.executable,str(script),str(rom),'--out',str(out)],
                                   capture_output=True,text=True)
            self.assertEqual(process.returncode,0,process.stderr)
            r=json.loads(out.read_text())
            self.assertTrue(r['all_anchors_verified'])
            self.assertEqual(r['increment_edge_cases']['21'],0)
            self.assertEqual(r['decrement_edge_cases']['0'],21)

if __name__=='__main__':unittest.main()
