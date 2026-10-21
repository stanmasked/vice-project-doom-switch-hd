"""ROM-free tests for opt-in FCEUX window metadata integrity."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_fceux_capture import audit_directory
from test_audit_private_fceux_capture import capture, replace_meta


def windowed(root,frame,start=112,stop=128,scope="selected_frame_window_only"):
    meta=capture(root,frame,screen=False,interval=8)
    with meta.open("a",encoding="utf8") as f:
        f.write(f"capture_window_start={start}\n")
        f.write(f"capture_window_stop={stop}\n")
        f.write(f"register_log_scope={scope}\n")
    return meta


class WindowMetadataTests(unittest.TestCase):
    def test_valid_windowed_capture_pair(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            windowed(root,120)
            windowed(root,128)
            result=audit_directory(root)
            self.assertTrue(result["capture_window_contract_consistent"])
            self.assertEqual(result["capture_count"],2)
            self.assertFalse(result["actual_first_stage_proven"])

    def test_legacy_no_window_remains_supported(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120,screen=False)
            self.assertFalse(audit_directory(root)["capture_window_contract_consistent"])

    def test_reject_frame_outside_window(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            windowed(root,120,start=128,stop=136)
            with self.assertRaisesRegex(ValueError,"outside declared"):
                audit_directory(root)

    def test_reject_incomplete_window_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            meta=windowed(root,120)
            replace_meta(meta,"capture_window_stop=128\n","")
            with self.assertRaisesRegex(ValueError,"incomplete capture-window"):
                audit_directory(root)

    def test_reject_mixed_window_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            windowed(root,120)
            windowed(root,128,start=104,stop=128)
            with self.assertRaisesRegex(ValueError,"mixed capture-window"):
                audit_directory(root)

    def test_reject_window_with_no_register_scope(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            windowed(root,120,scope="all_prior_frames")
            with self.assertRaisesRegex(ValueError,"unsupported register log scope"):
                audit_directory(root)


if __name__=="__main__":
    unittest.main()
