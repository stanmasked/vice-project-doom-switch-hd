"""Pure synthetic 1280x720 RGB24 test frames; no original game pixels."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_nexium_road_review import ORIGINAL
from audit_nexium_road_x11_shape import ROWS,RGB_BORDER,RGB_FILL,RGB_PANEL
from audit_nexium_road_x11_sweep import validate_sweep

W,H=1280,720
BACKGROUND=bytes((38,43,54))


def fake(first:int|None,last:int|None=None)->bytes:
    payload=bytearray(BACKGROUND*(W*H))
    if first is not None:
        assert last is not None
        for y in ROWS:
            base=y*W*3
            payload[base+(first-6)*3:base+(first-5)*3]=RGB_PANEL
            payload[base+(first-5)*3:base+first*3]=RGB_BORDER*5
            payload[base+first*3:base+(last+1)*3]=RGB_FILL*(last-first+1)
            payload[base+(last+1)*3:base+(last+6)*3]=RGB_BORDER*5
            payload[base+(last+6)*3:base+(last+7)*3]=RGB_PANEL
    return bytes(payload)


def fixtures():
    scale=0.9635
    offset=23.0
    screens=[]
    for movie,left,right in ORIGINAL:
        if movie==0:
            screens.append(fake(None))
        else:
            # Predict synthetic GUI scaling from source-only numeric interval.
            x0=round((left*5+5)*scale+offset)
            x1=round((((right+1)*5)-6)*scale+offset)
            screens.append(fake(x0,x1))
    return screens


class SevenScreenshotImageTests(unittest.TestCase):
    def expect_bad(self,fn):
        rows=fixtures()
        fn(rows)
        with self.assertRaises(ValueError):
            validate_sweep(rows)
    def test_seven_synthetic_frames_and_off(self):
        data=validate_sweep(fixtures())
        self.assertEqual(data["real_x11_reference_frames"],7)
        self.assertEqual(data["real_x11_off_frames"],1)
        self.assertTrue(data["source_image_lateral_shift_visible"])
        self.assertFalse(data["original_game_camera_speed_proven"])
    def test_missing_one_screenshot(self):
        self.expect_bad(lambda a:a.pop(5))
    def test_truncated_frame(self):
        self.expect_bad(lambda a:a.__setitem__(3,a[3][:-3]))
    def test_duplicated_wide_reference(self):
        self.expect_bad(lambda a:a.__setitem__(4,a[0]))
    def test_source_shift_missing_at_frame_920(self):
        self.expect_bad(lambda a:a.__setitem__(6,a[5]))
    def test_source_narrowing_wrong_at_frame_784(self):
        self.expect_bad(lambda a:a.__setitem__(3,a[2]))
    def test_different_gui_scale_on_one_frame(self):
        self.expect_bad(lambda a:a.__setitem__(2,fake(430,820)))
    def test_stale_off_screenshot(self):
        self.expect_bad(lambda a:a.__setitem__(7,a[4]))
    def test_corrupted_edge_rgb(self):
        def corrupt(a):
            img=bytearray(a[1])
            first=346
            y=ROWS[0]
            img[(y*W+first-1)*3:(y*W+first)*3]=bytes((2,3,4))
            a[1]=bytes(img)
        self.expect_bad(corrupt)
    def test_horizontal_displacement_wrong(self):
        self.expect_bad(lambda a:a.__setitem__(6,fake(520,930)))
    def test_expected_source_frame_sequence(self):
        self.assertEqual([t[0] for t in ORIGINAL],
            [600,744,760,784,800,840,920,0])


if __name__=="__main__":
    unittest.main()
