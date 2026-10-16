"""ROM-free invented 6502 fragments for stage35 pointer-provenance audit."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_indirect_pointer import (ANCHORS,BANK_SIZE,PRG_SIZE,read_prg,verify,
                                    pointer_emulation,direct_candidate_writers,inspect)

def invented_prg():
    prg=bytearray(PRG_SIZE)
    for _,bank,off,signature in ANCHORS:
        raw=bytes.fromhex(signature)
        prg[bank*BANK_SIZE+off:bank*BANK_SIZE+off+len(raw)]=raw
    return prg

class PointerAuditTests(unittest.TestCase):
    def test_three_verified_anchors(self):
        report=inspect(bytes(invented_prg()))
        self.assertTrue(report['all_anchors_verified'])
        self.assertEqual([x['name'] for x in report['anchor_status']],
                         ['pointer_table_lookup','consumer_decoder_start','consumer_direct_call'])
        self.assertEqual([x['physical_prg_bank'] for x in report['anchor_status']],[12,14,14])

    def test_corrupt_each_anchor_is_rejected(self):
        for name,bank,off,_ in ANCHORS:
            data=invented_prg()
            data[bank*BANK_SIZE+off]^=0x80
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,name):
                verify(bytes(data))
            self.assertFalse(all(x['signature_verified'] for x in verify(bytes(data),False)))

    def test_cpu_carry_differs_from_naive_triple_index(self):
        for i in (0,1,2,10,40,46,85):
            self.assertEqual(pointer_emulation(i),0x8376+3*i)
        self.assertEqual(pointer_emulation(86),0x8379)
        self.assertNotEqual(pointer_emulation(86),0x8376+3*86)
        for bad in (-1,256,True,1.2):
            with self.assertRaises(ValueError):pointer_emulation(bad)

    def test_raw_writers_are_not_claimed_executed(self):
        data=invented_prg()
        off=4*BANK_SIZE+133
        data[off:off+4]=bytes([0x85,0xAA,0x85,0xAB])
        hits=direct_candidate_writers(bytes(data))
        self.assertTrue(any(x['bank']==12 and x['offset']==0x0362 and
                            x['target']=='$AA' for x in hits))
        self.assertTrue(any(x['bank']==12 and x['offset']==0x0368 and
                            x['target']=='$AB' for x in hits))
        self.assertTrue(any(x['bank']==4 and x['offset']==133 for x in hits))
        self.assertTrue(all('not_proven_executed' in x['confidence'] for x in hits))

    def test_rom_header_and_trainer_guards(self):
        h=bytearray(16);h[:4]=b'NES\x1a';h[4]=8;h[6]=0x40
        prg=bytes(invented_prg())
        self.assertEqual(read_prg(bytes(h)+prg),prg)
        h[6]=0x44
        self.assertEqual(read_prg(bytes(h)+bytes(512)+prg),prg)
        for bad in (bytes(16),bytes(h)+prg,bytes(h)+bytes(512)+prg[:200]):
            with self.assertRaises(ValueError):read_prg(bad)

    def test_cli_on_synthetic_rom(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            h=bytearray(16);h[:4]=b'NES\x1a';h[4]=8;h[6]=0x40
            rom=root/'invented.nes'
            rom.write_bytes(bytes(h)+bytes(invented_prg()))
            out=root/'report.json'
            script=Path(__file__).resolve().parents[1]/'tools/audit_indirect_pointer.py'
            p=subprocess.run([sys.executable,str(script),str(rom),'--out',str(out)],
                             capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            report=json.loads(out.read_text())
            self.assertTrue(report['all_anchors_verified'])
            self.assertTrue(any(r['hypothetical_ram_92']==86 and
                not r['matches_base_plus_3index'] for r in report['hypothetical_index_examples']))

if __name__=='__main__':unittest.main()
