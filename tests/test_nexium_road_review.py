"""Only synthesized sources; no NES original pixels or movie data."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_nexium_road_review import ORIGINAL,validate,KEYS

def make_records():
    result=[]
    for seq,(frame,left,right) in enumerate(ORIGINAL,1):
        values={
            "seq":seq,"original_frame":frame,"drive_frame":seq*4,
            "left_hd":left*5 if frame else 0,
            "right_hd":(right+1)*5-1 if frame else 0,
            "outside_left":"ff22180e" if frame else "00000000",
            "edge_left":"ff75bee9" if frame else "00000000",
            "edge_right":"ff75bee9" if frame else "00000000",
            "outside_right":"ff22180e" if frame else "00000000",
            "off_pixel":"00000000" if frame else "ff4c503d",
            "car_pixel":"ff3f2fa3","hud_pixel":"ff5b55d3",
            "health":5,"flash":0,"platform_fp":"abcdef1234567890",
            "source":"libnx_drawScene","source_art":"none",
            "collision_proven":0
        }
        assert set(values)==KEYS
        result.append("VPD_ROAD_REVIEW_V1 "+" ".join(
            f"{k}={v}" for k,v in values.items()))
    return result

class NativeRoadReviewAuditTests(unittest.TestCase):
    def check_bad(self,edit):
        lines=make_records()
        edit(lines)
        with self.assertRaises(ValueError):
            validate(lines)
    def test_synthetic_native_eight_events(self):
        validate(make_records())
    def test_absent_one_source_sample(self):
        self.check_bad(lambda lines:lines.pop(4))
    def test_duplicate_guest_sample(self):
        self.check_bad(lambda lines:lines.__setitem__(4,lines[3]))
    def test_wrong_observed_movie_frame(self):
        self.check_bad(lambda lines:lines.__setitem__(
            4,lines[4].replace("original_frame=800","original_frame=801")))
    def test_wrong_right_inclusive_hd_edge(self):
        self.check_bad(lambda lines:lines.__setitem__(
            4,lines[4].replace("right_hd=779","right_hd=780")))
    def test_wrong_guest_panel_pixel(self):
        self.check_bad(lambda lines:lines.__setitem__(
            2,lines[2].replace("outside_right=ff22180e","outside_right=ff123456")))
    def test_wrong_guest_border_pixel(self):
        self.check_bad(lambda lines:lines.__setitem__(
            2,lines[2].replace("edge_left=ff75bee9","edge_left=00000000")))
    def test_guest_off_must_clear_overlay(self):
        self.check_bad(lambda lines:lines.__setitem__(
            7,lines[7].replace("off_pixel=ff4c503d","off_pixel=ff22180e")))
    def test_platform_fingerprint_changed(self):
        self.check_bad(lambda lines:lines.__setitem__(
            6,lines[6].replace("platform_fp=abcdef1234567890",
                               "platform_fp=abcdef1234567891")))
    def test_fake_controller_frame(self):
        self.check_bad(lambda lines:lines.__setitem__(
            6,lines[6].replace("drive_frame=28","drive_frame=24")))
    def test_wrong_car_source_pixel(self):
        self.check_bad(lambda lines:lines.__setitem__(
            1,lines[1].replace("car_pixel=ff3f2fa3","car_pixel=00000000")))
    def test_unexpected_payload_field_rejected(self):
        self.check_bad(lambda lines:lines.__setitem__(
            0,lines[0]+" original_rom=/private/file.nes"))
if __name__=="__main__":
    unittest.main()
