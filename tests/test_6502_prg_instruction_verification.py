"""Stage57 private-image verification uses invented PRG bytes only."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from verify_6502_prg_instruction import verify,PRG_BYTES
from test_joint_cpu_context_validation import JointContextTests

class BankByteVerificationTests(unittest.TestCase):
    def setUp(self):
        self.case=JointContextTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.image=Path(self.case.temp.name)/'synthetic.prg'
        data=bytearray(PRG_BYTES)
        offset=12*8192+0x35B
        data[offset:offset+3]=bytes.fromhex('AD5C83')
        self.image.write_bytes(data)
    def check(self,seq=1,code='AD5C83'):
        return verify(self.case.trace,self.case.meta,self.image,
                      exec_seq=seq,instruction_hex=code)
    def test_unknown_bank_not_attributed(self):
        self.assertEqual(self.check()['status'],'unresolved_bank')
    def test_known_bank_matches(self):
        self.case.rows.append(['19','5','EXEC','835B','unknown','12',
                              '01','02','03','04','unknown'])
        self.case.write_rows()
        self.case.meta.write_text(self.case.meta.read_text().replace(
            'events_recorded=4','events_recorded=5'))
        r=self.check(5)
        self.assertTrue(r['bytes_match'])
        self.assertEqual(r['physical_offset'],12*8192+0x35B)
        self.assertFalse(r['instruction_causality_proven'])
    def test_not_exec(self):
        with self.assertRaisesRegex(ValueError,'not EXEC'):self.check(2)
    def test_headered_image_rejected(self):
        self.image.write_bytes(b'NES'+self.image.read_bytes())
        with self.assertRaisesRegex(ValueError,'128 KiB'):self.check()
    def test_bad_instruction_hex(self):
        with self.assertRaisesRegex(ValueError,'instruction bytes'):
            self.check(code='NOT HEX')
    def test_capture_incomplete_rejected(self):
        self.case.meta.write_text(self.case.meta.read_text().replace(
            'events_dropped=0','events_dropped=1').replace('complete=yes','complete=no'))
        with self.assertRaisesRegex(ValueError,'Incomplete'):self.check()

if __name__=='__main__':unittest.main()
