"""Stage48: refuse to classify address-only PRG reads as level data."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from triage_prg_reads import triage
from test_prg_capture_completeness import VerifiedCaptureTests

class Stage48Tests(unittest.TestCase):
    def test_unclassified_reads(self):
        case=VerifiedCaptureTests()
        case.setUp()
        try:
            result=triage(case.trace,case.meta,min_run=1)
            self.assertEqual(len(result['candidates']),3)
            self.assertEqual(result['confirmed_level_data_ranges'],[])
            for c in result['candidates']:
                self.assertEqual(c['role'],'indeterminate_code_or_data')
                self.assertFalse(c['instruction_pc_observed'])
                self.assertFalse(c['level_data_proven'])
        finally:
            case.doCleanups()
    def test_reject_dropped_trace(self):
        case=VerifiedCaptureTests()
        case.setUp()
        try:
            case.write_meta(dropped=1,complete='no')
            with self.assertRaisesRegex(ValueError,'Incomplete'):
                triage(case.trace,case.meta)
        finally:
            case.doCleanups()

if __name__=='__main__':unittest.main()
