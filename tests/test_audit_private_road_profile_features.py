"""Independent invented source geometry exercises; no original RGB data."""
from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from test_audit_private_legacy_road_geometry import synthetic
from audit_private_road_profile_features import profile

def fixture():
    data=synthetic()
    # These endpoints are deliberately invented independently of real source
    # captures. The seven published anchor values are retained from fixture.
    for frame,left,right in [(864,84,171),(904,116,203)]:
        row=next(x for x in data["frames"] if x["frame"]==frame)
        row["observed_left_edge"]=left
        row["observed_right_edge"]=right
        row["observed_width"]=right-left+1
        row["observed_center_x"]=(left+right)/2
    valid=[x for x in data["frames"] if x["roi_valid"]]
    data["summary"]["minimum_observed_width"]=min(
        x["observed_width"] for x in valid)
    data["summary"]["maximum_observed_width"]=max(
        x["observed_width"] for x in valid)
    data["summary"]["minimum_observed_center_x"]=min(
        x["observed_center_x"] for x in valid)
    data["summary"]["maximum_observed_center_x"]=max(
        x["observed_center_x"] for x in valid)
    return data

class RoadProfileTests(unittest.TestCase):
    def test_valid_invented_profile(self):
        s=profile(fixture())
        self.assertEqual(s["accepted_samples"],37)
        self.assertEqual(s["ambiguous_samples"],4)
        self.assertEqual(s["continuous_valid_runs"],[
            {"first_frame":600,"last_frame":704,"samples":14},
            {"first_frame":744,"last_frame":920,"samples":23},
        ])
        self.assertEqual(
            s["observed_image_space_changes"]["visible_narrowing"][
                "measured_difference_px"],-67)
        self.assertEqual(
            s["observed_image_space_changes"]["visible_widening"][
                "measured_difference_px"],32)
        self.assertEqual(
            s["observed_image_space_changes"]["lateral_image_shift"][
                "measured_difference_px"],32)
        self.assertFalse(s["camera_speed_proven"])
        self.assertFalse(s["collision_boundaries_proven"])
        self.assertFalse(s["interpolation_across_missing_frames_permitted"])
        self.assertNotIn("frame_coordinates",s)
    def test_duplicate_rgb_frame_rejected(self):
        r=fixture()
        r["frames"][15]=copy.deepcopy(r["frames"][14])
        with self.assertRaises(ValueError):profile(r)
    def test_broken_report_summary_rejected(self):
        r=fixture()
        r["summary"]["maximum_observed_center_x"]=200
        with self.assertRaises(ValueError):profile(r)
    def test_broken_published_anchor_rejected(self):
        r=fixture()
        r["frames"][20]["observed_width"]=100
        with self.assertRaises(ValueError):profile(r)
    def test_rejected_ambiguous_cannot_have_fake_pixels(self):
        r=fixture()
        r["frames"][14]["observed_left_edge"]=65
        with self.assertRaises(ValueError):profile(r)
    def test_unsupported_source_hash_claim_not_added(self):
        s=profile(fixture())
        self.assertFalse(s["source_rom_fm2_identity_verified_by_this_report"])
        self.assertNotIn("rom_sha256",s)
    def test_original_pixel_coordinates_do_not_escape_in_summary(self):
        s=profile(fixture())
        self.assertNotIn("observed_left_edge",str(s))
        self.assertNotIn("observed_right_edge",str(s))
        self.assertNotIn("original_rom",str(s))
    def test_ambiguous_gap_not_interpolated(self):
        s=profile(fixture())
        first,second=s["continuous_valid_runs"]
        self.assertEqual(first["last_frame"],704)
        self.assertEqual(second["first_frame"],744)
        self.assertTrue(s["interpolation_across_missing_frames_permitted"] is False)

if __name__=="__main__":
    unittest.main()
