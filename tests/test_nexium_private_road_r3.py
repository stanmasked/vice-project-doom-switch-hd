"""Invented data only; independent falsification tests for 37+OFF."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_nexium_private_road_r3 import validate_records,source_rows
from generate_synthetic_road_bundle import synthetic_bundle

FIELDS={
    "seq":0,"source_frame":0,"drive_frame":0,
    "left_hd":0,"right_hd":0,
    "outside_left":"00000000","edge_left":"00000000",
    "edge_right":"00000000","outside_right":"00000000",
    "marker_pixel":"00000000","off_pixel":"00000000",
    "car_pixel":"ff3f2fa3","hud_pixel":"ff5b55d3",
    "health":5,"flash":0,"platform_fp":"aaabbbcccddd1111",
    "source":"libnx_framebuffer","original_art":"none",
    "camera_collision_proven":"no",
}
def records():
    all_rows=source_rows(synthetic_bundle())
    lines=[]
    for i in range(1,39):
        attrs=FIELDS.copy()
        attrs["seq"]=i
        attrs["drive_frame"]=i*3
        sample=all_rows[i-1] if i<=37 else None
        attrs["source_frame"]=sample[0] if sample else 0
        if sample:
            _,left,right=sample
            attrs.update(left_hd=left*5,right_hd=(right+1)*5-1,
                         outside_left="ff22180e",outside_right="ff22180e",
                         edge_left="ff75bee9",edge_right="ff75bee9",
                         marker_pixel="ff75bee9")
        else:
            attrs["off_pixel"]="ff4c503d"
        lines.append("VPD_PRIVATE_ROAD_R3_V1 "+
                     " ".join(f"{k}={v}" for k,v in attrs.items()))
    return lines
class PrivateR3Tests(unittest.TestCase):
    def fail(self,modify):
        lines=records()
        modify(lines)
        with self.assertRaises(ValueError):
            validate_records(lines,synthetic_bundle())
    def test_38_valid_source_owned_samples(self):
        validate_records(records(),synthetic_bundle())
    def test_one_missing_guest_event(self):
        self.fail(lambda v:v.pop(21))
    def test_duplicate_guest_frame(self):
        self.fail(lambda v:v.__setitem__(5,v[4]))
    def test_forged_frame_800(self):
        self.fail(lambda v:v.__setitem__(21,v[21].replace(
            "source_frame=800","source_frame=808")))
    def test_wrong_edge_color(self):
        self.fail(lambda v:v.__setitem__(21,v[21].replace(
            "edge_right=ff75bee9","edge_right=00000000")))
    def test_wrong_37_marker(self):
        self.fail(lambda v:v.__setitem__(9,v[9].replace(
            "marker_pixel=ff75bee9","marker_pixel=ff000000")))
    def test_bad_source_right_interval(self):
        self.fail(lambda v:v.__setitem__(0,v[0].replace(
            "right_hd=944","right_hd=945")))
    def test_off_still_active(self):
        self.fail(lambda v:v.__setitem__(37,v[37].replace(
            "off_pixel=ff4c503d","off_pixel=ff22180e")))
    def test_stale_native_frame(self):
        self.fail(lambda v:v.__setitem__(11,v[11].replace(
            "drive_frame=36","drive_frame=33")))
    def test_changed_platform(self):
        self.fail(lambda v:v.__setitem__(22,v[22].replace(
            "platform_fp=aaabbbcccddd1111",
            "platform_fp=aaabbbcccddd1112")))
    def test_bad_hud(self):
        self.fail(lambda v:v.__setitem__(17,v[17].replace(
            "hud_pixel=ff5b55d3","hud_pixel=00000000")))
    def test_reject_private_file_paths(self):
        self.fail(lambda v:v.__setitem__(
            0,v[0]+" source_rom=/private/rom.nes"))
    def test_changed_synthetic_bundle(self):
        altered=bytearray(synthetic_bundle());altered[-1]^=1
        with self.assertRaises(ValueError):
            validate_records(records(),bytes(altered))
if __name__=="__main__":
    unittest.main()
