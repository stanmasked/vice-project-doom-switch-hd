"""Stage60 cross-stage synthetic PRG -> MMC3 -> CPU read integration."""
import hashlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from correlate_verified_prg_reads import correlate
from test_6502_prg_instruction_verification import BankByteVerificationTests

class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.fixture=BankByteVerificationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.case.rows.extend([
            ['19','5','EXEC','835B','unknown','12','01','02','03','04','unknown'],
            ['19','6','READ','835C','AB','12','01','02','03','04','unknown']
        ])
        self.fixture.case.write_rows()
        self.fixture.case.meta.write_text(
            self.fixture.case.meta.read_text().replace('events_recorded=4',
                                                       'events_recorded=6'))
    def check(self,expected):
        return correlate(self.fixture.case.trace,self.fixture.case.meta,
                         self.fixture.image,exec_seq=5,opcode_hex='AD5C83',
                         expected_prg_sha256=expected)
    def test_attested_image_and_matching_address(self):
        expected=hashlib.sha256(self.fixture.image.read_bytes()).hexdigest()
        result=self.check(expected)
        self.assertEqual(result['status'],'local_instruction_bytes_match')
        self.assertEqual(len(result['candidate_reads']),1)
        self.assertFalse(result['instruction_caused_read_proven'])
        self.assertFalse(result['level_data_proven'])
    def test_wrong_image_hash_blocks_all_candidates(self):
        result=self.check('f'*64)
        self.assertEqual(result['status'],'prg_identity_mismatch')
        self.assertEqual(result['candidate_reads'],[])
    def test_intervening_mmc3_write_blocks_candidate(self):
        self.fixture.case.rows[5]=['19','6','SELECT','8000','06','12',
                                  '01','02','03','04','unknown']
        self.fixture.case.rows.append(['19','7','READ','835C','AB','12',
                                       '01','02','03','04','unknown'])
        self.fixture.case.write_rows()
        self.fixture.case.meta.write_text(
            self.fixture.case.meta.read_text().replace('events_recorded=6',
                                                       'events_recorded=7'))
        expected=hashlib.sha256(self.fixture.image.read_bytes()).hexdigest()
        result=self.check(expected)
        self.assertEqual(result['candidate_reads'],[])
        self.assertEqual(result['search_stopped_by'],'execution_or_mapper_event')

if __name__=='__main__': unittest.main()
