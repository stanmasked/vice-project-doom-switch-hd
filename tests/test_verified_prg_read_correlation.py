"""Stage58: synthetic PRG byte attestation gates CPU read candidates."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from correlate_verified_prg_reads import correlate
from test_6502_prg_instruction_verification import BankByteVerificationTests

class Stage58Tests(BankByteVerificationTests):
    def setup_neighbor(self):
        self.case.rows.append(['19','5','EXEC','835B','unknown','12',
                               '01','02','03','04','unknown'])
        self.case.rows.append(['19','6','READ','835C','AB','12',
                               '01','02','03','04','unknown'])
        self.case.write_rows()
        self.case.meta.write_text(self.case.meta.read_text().replace(
            'events_recorded=4','events_recorded=6'))
    def test_verified_instruction_address_match_is_noncausal(self):
        self.setup_neighbor()
        result=correlate(self.case.trace,self.case.meta,self.image,
                         exec_seq=5,opcode_hex='AD5C83')
        self.assertEqual(result['status'],'local_instruction_bytes_match')
        self.assertEqual(len(result['candidate_reads']),1)
        self.assertFalse(result['instruction_caused_read_proven'])
        self.assertFalse(result['level_data_proven'])
    def test_mismatching_instruction_never_reports_candidates(self):
        self.setup_neighbor()
        result=correlate(self.case.trace,self.case.meta,self.image,
                         exec_seq=5,opcode_hex='AD5D83')
        self.assertEqual(result['status'],'instruction_not_verified')
        self.assertEqual(result['candidate_reads'],[])
    def test_missing_mapper_state_never_reports_candidates(self):
        result=correlate(self.case.trace,self.case.meta,self.image,
                         exec_seq=1,opcode_hex='AD5C83')
        self.assertEqual(result['verification']['status'],'unresolved_bank')
        self.assertEqual(result['candidate_reads'],[])
    def test_incomplete_trace_rejected(self):
        self.setup_neighbor()
        self.case.meta.write_text(self.case.meta.read_text().replace(
            'events_dropped=0','events_dropped=1').replace('complete=yes','complete=no'))
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            correlate(self.case.trace,self.case.meta,self.image,
                      exec_seq=5,opcode_hex='AD5C83')

if __name__=='__main__':unittest.main()
