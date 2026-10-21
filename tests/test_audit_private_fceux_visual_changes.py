"""Invented screen palettes only; no commercial NES screenshots used."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_fceux_storyboard import PAL_SIZE
from audit_private_fceux_visual_changes import analyze,pair_metrics
from test_audit_private_fceux_storyboard import capture,replace


def fixture(root,values=(16,16,16)):
    metas=[]
    for frame,value in zip((8,16,24),values):
        meta,_,pal=capture(root,frame)
        pal.write_bytes(bytes([value])*PAL_SIZE)
        metas.append(meta)
    return metas


class PrivateVisualChangeTests(unittest.TestCase):
    def test_identical_palette_is_not_a_stage(self):
        with tempfile.TemporaryDirectory() as d:
            fixture(Path(d))
            result=analyze(d)
            self.assertEqual(result["candidate_count"],0)
            self.assertEqual(result["compared_frame_pairs"],2)
            self.assertTrue(result["complete_window_verified"])
            self.assertFalse(result["original_level_boundaries_proven"])

    def test_distinct_palette_flags_one_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            fixture(Path(d),(16,31,31))
            result=analyze(d)
            self.assertEqual(result["candidate_count"],1)
            self.assertEqual(result["candidates"][0]["frame_before"],8)
            self.assertEqual(result["candidates"][0]["frame_after"],16)
            self.assertEqual(result["candidates"][0]["sampled_palette_distribution_shift"],1.0)

    def test_half_screen_transition_detected_at_lower_threshold(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            fixture(root)
            pal=root/"frame_000016.pal.bin"
            pal.write_bytes(bytes([16])*(PAL_SIZE//2)+bytes([31])*(PAL_SIZE//2))
            result=analyze(root,min_pixel_change=.45,min_palette_shift=.45)
            self.assertGreaterEqual(result["candidate_count"],1)

    def test_high_unknown_palette_suppresses_claim(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            metas=fixture(root)
            (root/"frame_000016.pal.bin").write_bytes(bytes([254])*PAL_SIZE)
            replace(metas[1],"invalid_palette_values=0","invalid_palette_values="+str(PAL_SIZE))
            result=analyze(root)
            self.assertEqual(result["candidate_count"],0)
            self.assertEqual(result["uncertain_pairs_due_to_unavailable_palette"],2)

    def test_malformed_palette_fails_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            fixture(root)
            (root/"frame_000008.pal.bin").write_bytes(bytes([64])*PAL_SIZE)
            with self.assertRaisesRegex(ValueError,"NES palette value"):
                analyze(root)

    def test_strict_rejects_missing_scheduled_frame(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,8)
            capture(root,24)
            with self.assertRaisesRegex(ValueError,"window incomplete"):
                analyze(root)

    def test_incomplete_exploratory_mode_remains_unproven(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,8)
            capture(root,24)
            r=analyze(root,require_complete=False)
            self.assertFalse(r["complete_window_verified"])

    def test_reject_unbounded_threshold_and_stride(self):
        with tempfile.TemporaryDirectory() as d:
            fixture(Path(d))
            with self.assertRaisesRegex(ValueError,"stride"):
                analyze(d,stride=0)
            with self.assertRaisesRegex(ValueError,"thresholds"):
                analyze(d,min_palette_shift=1.5)

    def test_pair_histogram_distance(self):
        a=bytes([16,16,16,16])
        b=bytes([16,16,31,31])
        p,h,u=pair_metrics(a,b)
        self.assertEqual((p,h,u),(.5,.5,0))


if __name__=="__main__":
    unittest.main()
