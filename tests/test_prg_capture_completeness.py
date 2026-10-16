"""Stage46 metadata completeness gate: entirely synthetic captures."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_prg_read_mapping import audit_verified
from test_prg_read_mapping import fixture

class VerifiedCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.trace=root/'stage45_prg_reads.tsv'
        fixture(self.trace)
        self.meta=root/'stage45_prg_reads.meta.txt'
        self.write_meta()
    def write_meta(self,dropped=0,complete='yes',recorded=8):
        self.meta.write_text('\n'.join([
            'format=vice_stage45_prg_reads_v1',
            'events_recorded='+str(recorded),
            'events_dropped='+str(dropped),
            'complete='+complete,
            'initial_mmc3_mode=unknown',
            'read_provenance=registerread_callback_no_pc_proof',
            'read_value_provenance=address_only_fceux_zero_sentinel'])+'\n',encoding='utf8')
    def test_matching_complete_capture(self):
        result=audit_verified(self.trace,self.meta)
        self.assertTrue(result['capture_metadata_verified'])
        self.assertEqual(result['events_recorded'],8)
    def test_legacy_read_value_provenance_refused(self):
        self.meta.write_text(self.meta.read_text().replace(
            'read_value_provenance=address_only_fceux_zero_sentinel\\n',''))
        with self.assertRaisesRegex(ValueError,'provenance'):
            audit_verified(self.trace,self.meta)

    def test_overflow_refused(self):
        self.write_meta(dropped=1,complete='no')
        with self.assertRaisesRegex(ValueError,'Incomplete'):audit_verified(self.trace,self.meta)
    def test_false_complete_refused(self):
        self.write_meta(dropped=1,complete='yes')
        with self.assertRaisesRegex(ValueError,'Contradictory'):audit_verified(self.trace,self.meta)
    def test_truncated_trace_refused(self):
        self.write_meta(recorded=9)
        with self.assertRaisesRegex(ValueError,'count mismatch'):audit_verified(self.trace,self.meta)
    def test_missing_metadata_refused(self):
        self.meta.unlink()
        with self.assertRaises(FileNotFoundError):audit_verified(self.trace,self.meta)
    def test_forged_provenance_refused(self):
        self.meta.write_text(self.meta.read_text().replace('registerread_callback_no_pc_proof','read_proven'))
        with self.assertRaisesRegex(ValueError,'provenance'):audit_verified(self.trace,self.meta)

if __name__=='__main__':unittest.main()
