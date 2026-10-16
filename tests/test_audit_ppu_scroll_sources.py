"""Synthetic 6502 fragments only, never original game ROM or graphics."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_ppu_scroll_sources import EMITTER,CALL,BANK_BYTES,address,inspect,store_candidates

def fake_prg():
    data=bytearray(16*BANK_BYTES)
    for pc,op,_,_ in EMITTER:
        start=15*BANK_BYTES+pc-0xE000
        data[start:start+len(op)]=bytes(op)
    pc,op,_=CALL
    start=15*BANK_BYTES+pc-0xE000
    data[start:start+len(op)]=bytes(op)
    return data

class StaticScrollAuditTests(unittest.TestCase):
    def test_verified_sources_and_known_calls(self):
        result=inspect(bytes(fake_prg()))
        self.assertTrue(result['all_emitter_anchors_verified'])
        self.assertEqual(result['scroll_sources']['first_PPUSCROLL_write'],'zero-page $0B')
        self.assertEqual(result['scroll_sources']['second_PPUSCROLL_write'],'zero-page $0D')
        self.assertTrue(result['caller']['opcode_verified'])
        self.assertEqual({m['cpu_address_if_fixed'] for m in
                          result['fixed_bank_ppuscroll_candidates']},{'$E8EC','$E8F1'})
        self.assertEqual(result['prg_bank_register_write_candidate_counts'][15]['pattern_count'],3)

    def test_changed_scroll_byte_rejected(self):
        data=fake_prg()
        data[15*BANK_BYTES+0xE8EF-0xE000+1]=0x0E
        with self.assertRaisesRegex(ValueError,'E8EF'):inspect(bytes(data))
        report=inspect(bytes(data),strict=False)
        self.assertFalse(report['all_emitter_anchors_verified'])
        self.assertEqual(sum(not i['opcode_verified'] for i in report['audited_instructions']),1)

    def test_unknown_caller_rejected(self):
        data=fake_prg()
        data[15*BANK_BYTES+CALL[0]-0xE000]=0
        with self.assertRaisesRegex(ValueError,'caller'):inspect(bytes(data))

    def test_switched_bank_offsets_not_unconditionally_mapped(self):
        data=fake_prg()
        pos=2*BANK_BYTES+0x122
        data[pos:pos+3]=bytes([0x8E,0x05,0x20])
        candidates=store_candidates(bytes(data))
        self.assertEqual(candidates[2]['byte_pattern_count'],1)
        match=candidates[2]['matches'][0]
        self.assertEqual(match['candidate_instruction'],'STX $2005')
        self.assertIsNone(match['cpu_address_if_fixed'])
        self.assertEqual(address(15,255),'$E0FF')

    def test_bounds_rejected(self):
        with self.assertRaises(ValueError):inspect(bytes(128))
        with self.assertRaises(ValueError):store_candidates(bytes(128))
        with self.assertRaises(ValueError):address(16,0)

    def test_cli_on_invented_rom(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            header=bytearray(16)
            header[:4]=b'NES\x1a'
            header[4]=8
            header[6]=0x40
            rom=root/'invented.nes'
            rom.write_bytes(bytes(header)+bytes(fake_prg())+bytes(128*1024))
            report=root/'report.json'
            script=Path(__file__).resolve().parents[1]/'tools/audit_ppu_scroll_sources.py'
            process=subprocess.run([sys.executable,str(script),str(rom),'--out',str(report)],
                                   text=True,capture_output=True)
            self.assertEqual(process.returncode,0,process.stderr)
            self.assertTrue(json.loads(report.read_text())['all_emitter_anchors_verified'])

if __name__=='__main__':unittest.main()
