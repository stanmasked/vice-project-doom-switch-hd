"""Stage59 synthetic SHA256 input identity and diagnostics."""
import hashlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from correlate_verified_prg_reads import correlate
from test_6502_prg_instruction_verification import BankByteVerificationTests

class Stage59Tests(unittest.TestCase):
    def setUp(self):
        self.case=BankByteVerificationTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
    def run_check(self,sha):
        return correlate(self.case.case.trace,self.case.case.meta,self.case.image,
                         exec_seq=1,opcode_hex='AD5C83',
                         expected_prg_sha256=sha)
    def test_correct_digest_preserves_unknown_bank_reason(self):
        digest=hashlib.sha256(self.case.image.read_bytes()).hexdigest()
        result=self.run_check(digest)
        self.assertEqual(result['reason'],'unresolved_bank')
        self.assertEqual(result['candidate_reads'],[])
    def test_wrong_digest_rejects_before_processing(self):
        result=self.run_check('0'*64)
        self.assertEqual(result['status'],'prg_identity_mismatch')
        self.assertEqual(result['candidate_reads'],[])
    def test_invalid_digest_rejected(self):
        with self.assertRaisesRegex(ValueError,'SHA256'):
            self.run_check('bad')

if __name__=='__main__':unittest.main()
