"""Additional fabricated, ROM-free FCEUX v4 provenance regression tests."""
from pathlib import Path
import tempfile
import unittest

from audit_private_fceux_capture import audit_directory
from test_audit_private_fceux_capture import capture, replace_meta


class PrivateTraceProvenanceTests(unittest.TestCase):
    def test_valid_no_clock_v4_session(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120,screen=False)
            capture(root,240,screen=False)
            report=audit_directory(root)
            self.assertIs(report["cycle_trace_available"],False)

    def test_reject_missing_v4_clock_marker(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            path=capture(root,120,screen=False)
            replace_meta(path,"cycle_trace_available=no\n","")
            with self.assertRaisesRegex(ValueError,"cycle trace availability"):
                audit_directory(root)

    def test_reject_unsupported_cycle_epoch(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            path=capture(root,120,screen=False)
            replace_meta(path,"cycle_trace_counter_epoch=debugger_since_reset",
                         "cycle_trace_counter_epoch=wall_clock")
            with self.assertRaisesRegex(ValueError,"cycle counter epoch"):
                audit_directory(root)

    def test_reject_clock_mode_change_in_session(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120,screen=False)
            path=capture(root,240,screen=False)
            replace_meta(path,"cycle_trace_available=no",
                         "cycle_trace_available=yes")
            with self.assertRaisesRegex(ValueError,"mixed CPU cycle trace"):
                audit_directory(root)

    def test_reject_v3_v4_schema_mixture(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            path=capture(root,120,screen=False)
            capture(root,240,screen=False)
            replace_meta(path,"format=fceux_ppu_snapshot_v4",
                         "format=fceux_ppu_snapshot_v3")
            with self.assertRaisesRegex(ValueError,"mixed capture format"):
                audit_directory(root)

    def test_legacy_v3_format_is_supported(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            path=capture(root,120,screen=False)
            replace_meta(path,"format=fceux_ppu_snapshot_v4",
                         "format=fceux_ppu_snapshot_v3")
            replace_meta(path,"cycle_trace_available=no\n","")
            replace_meta(path,"cycle_trace_counter_epoch=debugger_since_reset\n","")
            report=audit_directory(root)
            self.assertIsNone(report["cycle_trace_available"])

    def test_reject_symlink_capture_root(self):
        with tempfile.TemporaryDirectory() as d:
            parent=Path(d)
            actual=parent/"owned"
            actual.mkdir()
            capture(actual,120,screen=False)
            alias=parent/"alias"
            try:
                alias.symlink_to(actual,target_is_directory=True)
            except (OSError,NotImplementedError) as exc:
                self.skipTest("symlink unsupported: "+str(exc))
            with self.assertRaisesRegex(ValueError,"non-symlink"):
                audit_directory(alias)


if __name__=="__main__":
    unittest.main()
