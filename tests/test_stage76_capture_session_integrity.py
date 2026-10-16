"""Stage76: pending-session metadata must not certify any old or new trace.

These regression fixtures are synthetic. No FCEUX or game content is used.
"""
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_dispatch_execution import analyze
from validate_pointer_access import validate as pointer_validate
from audit_prg_read_mapping import audit_verified
from validate_joint_trace import validate as joint_validate
from validate_joint_cpu_context import validate as context_validate
import test_dispatch_execution as dispatch_fixtures
import test_pointer_access_validation as pointer_fixtures
import test_prg_capture_completeness as prg_fixtures
import test_joint_trace_validation as joint_fixtures
import test_joint_cpu_context_validation as context_fixtures

PENDING='capture_in_progress=yes\n'

class SessionMetadataTests(unittest.TestCase):
    def prepare(self, fixture_type):
        instance=fixture_type()
        instance.setUp()
        self.addCleanup(instance.doCleanups)
        return instance

    def test_stage38_old_complete_metadata_replaced_by_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            trace,meta=dispatch_fixtures.fixture(Path(directory))
            self.assertTrue(analyze(trace,meta)['complete'])
            meta.write_text(PENDING,encoding='utf8')
            with self.assertRaises(ValueError):
                analyze(trace,meta)

    def test_stage41_pending_session_rejected(self):
        fixture=self.prepare(pointer_fixtures.PointerValidationTests)
        self.assertTrue(pointer_validate(fixture.log,fixture.meta)['complete'])
        fixture.meta.write_text(PENDING,encoding='utf8')
        with self.assertRaises(ValueError):
            pointer_validate(fixture.log,fixture.meta)

    def test_stage45_pending_session_rejected(self):
        fixture=self.prepare(prg_fixtures.VerifiedCaptureTests)
        self.assertTrue(audit_verified(fixture.trace,fixture.meta)['capture_complete'])
        fixture.meta.write_text(PENDING,encoding='utf8')
        with self.assertRaises(ValueError):
            audit_verified(fixture.trace,fixture.meta)

    def test_stage49_pending_session_rejected(self):
        fixture=self.prepare(joint_fixtures.JointTraceValidationTests)
        self.assertTrue(joint_validate(fixture.trace,fixture.meta)['complete'])
        fixture.meta.write_text(PENDING,encoding='utf8')
        with self.assertRaises(ValueError):
            joint_validate(fixture.trace,fixture.meta)

    def test_stage53_pending_session_rejected(self):
        fixture=self.prepare(context_fixtures.JointContextTests)
        self.assertTrue(context_validate(fixture.trace,fixture.meta)['complete'])
        fixture.meta.write_text(PENDING,encoding='utf8')
        with self.assertRaises(ValueError):
            context_validate(fixture.trace,fixture.meta)

    def test_truncated_finalize_cannot_prove_complete_stage53(self):
        fixture=self.prepare(context_fixtures.JointContextTests)
        fixture.meta.write_text('format=vice_stage53_joint_context_v1\n'
                                'complete=yes\n',encoding='utf8')
        with self.assertRaises(ValueError):
            context_validate(fixture.trace,fixture.meta)

if __name__=='__main__':
    unittest.main()
