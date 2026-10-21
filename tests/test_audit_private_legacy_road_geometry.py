"""Synthetic geometry. Do not embed private original FCEUX rows."""
from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_legacy_road_geometry import (
    LEGACY_AMBIGUOUS,validate_legacy_report
)
from audit_private_road_ppu_window import MOVIE_FRAMES, PUBLISHED_IMAGE


def synthetic():
    r={
        "schema":"vice-stage1-private-road-mask-scan-v1",
        "source":"invented FCEUX numeric fixture",
        "capture_start":600,"capture_stop":920,"interval_frames":8,
        "capture_count":41,"observed_callback_gaps":0,
        "capture_status":"complete local focused window",
        "methods":{
            "palette_or_rgb":"invented synthetic neutral fill",
            "scanlines_y":[120,140,160,180],
            "validity":"invented 3/4 threshold",
            "units":"source image px",
            "interpretation":"not actual collision geometry",
        },
        "frames":[],
        "limitations":["synthetic fixture; no actual ROM or FM2"],
        "summary":{},
    }
    for frame in MOVIE_FRAMES:
        if frame in LEGACY_AMBIGUOUS:
            r["frames"].append({
                "frame":frame,"roi_valid":False,"valid_scanline_count":2,
            })
            continue
        left,right=PUBLISHED_IMAGE.get(frame,(66,188))
        r["frames"].append({
            "frame":frame,"roi_valid":True,
            "observed_left_edge":left,"observed_right_edge":right,
            "observed_width":right-left+1,
            "observed_center_x":(left+right)/2,
            "valid_scanline_count":4,
        })
    good=[row for row in r["frames"] if row["roi_valid"]]
    widths=[x["observed_width"] for x in good]
    centers=[x["observed_center_x"] for x in good]
    r["summary"]={
        "valid_frames":37,"rejected_ambiguous_frames":4,
        "minimum_observed_width":min(widths),
        "maximum_observed_width":max(widths),
        "minimum_observed_center_x":min(centers),
        "maximum_observed_center_x":max(centers),
    }
    return r


class LegacyRoadTests(unittest.TestCase):
    def assert_bad(self,alter):
        r=synthetic()
        alter(r)
        with self.assertRaises(ValueError):
            validate_legacy_report(r)

    def test_valid_synthetic_numeric_window(self):
        result=validate_legacy_report(synthetic())
        self.assertEqual(result["numeric_road_slots"],41)
        self.assertEqual(result["accepted_visible_cross_sections"],37)
        self.assertEqual(result["ambiguous_cross_sections"],4)
        self.assertFalse(result["rom_fm2_hash_identity_confirmed_by_this_report"])
        self.assertNotIn("source",result)

    def test_missing_frame(self):
        self.assert_bad(lambda r:r["frames"].pop(10))
    def test_duplicate_frame(self):
        self.assert_bad(lambda r:r["frames"].__setitem__(
            10,copy.deepcopy(r["frames"][9])))
    def test_unexpected_raw_media_metadata(self):
        self.assert_bad(lambda r:r.update(original_rom_path="/private/a.nes"))
    def test_wrong_capture_callback_gaps(self):
        self.assert_bad(lambda r:r.update(observed_callback_gaps=1))
    def test_wrong_measurement_rows(self):
        self.assert_bad(lambda r:r["methods"].update(scanlines_y=[1,2,3,4]))
    def test_invalid_scanline_count_for_valid_row(self):
        self.assert_bad(lambda r:r["frames"][0].update(valid_scanline_count=2))
    def test_invalid_scanline_count_for_rejected_row(self):
        self.assert_bad(lambda r:r["frames"][14].update(valid_scanline_count=3))
    def test_rejected_frame_turned_accepted(self):
        self.assert_bad(lambda r:r["frames"][14].update(
            roi_valid=True,observed_left_edge=66,
            observed_right_edge=188,observed_width=123,
            observed_center_x=127.0,valid_scanline_count=4))
    def test_original_source_anchor_changed(self):
        self.assert_bad(lambda r:r["frames"][20].update(observed_left_edge=83))
    def test_inconsistent_width(self):
        self.assert_bad(lambda r:r["frames"][20].update(observed_width=93))
    def test_inconsistent_center(self):
        self.assert_bad(lambda r:r["frames"][20].update(observed_center_x=129.5))
    def test_bogus_summary(self):
        self.assert_bad(lambda r:r["summary"].update(maximum_observed_width=124))
    def test_boolean_as_integer_rejected(self):
        self.assert_bad(lambda r:r["frames"][20].update(observed_width=True))
    def test_invalid_marker_rejected(self):
        self.assert_bad(lambda r:r["frames"][0].update(roi_valid=1))
    def test_ambiguous_record_cannot_have_fake_width(self):
        self.assert_bad(lambda r:r["frames"][14].update(observed_width=100))
    def test_unverified_status_rejected(self):
        self.assert_bad(lambda r:r.update(capture_status="incomplete"))
    def test_source_of_measurement_must_be_identified(self):
        self.assert_bad(lambda r:r.update(source="unknown"))
    def test_legacy_source_report_does_not_inherit_identity_claims(self):
        r=synthetic()
        self.assertFalse(validate_legacy_report(r)[
            "rom_fm2_hash_identity_confirmed_by_this_report"])


if __name__=="__main__":
    unittest.main()
