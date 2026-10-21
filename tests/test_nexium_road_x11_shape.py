"""Fake RGB24 X11 screen fixtures only: no copyrighted NES pixels."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_nexium_road_x11_shape import (
    RGB_BORDER,RGB_FILL,RGB_PANEL,ROWS,validate_frames,
)

W,H=1280,720
DEFAULT=bytes((42,50,66))


def raster(first:int|None,last:int|None=None) -> bytes:
    screen=bytearray(DEFAULT*(W*H))
    if first is not None:
        assert last is not None
        for row in ROWS:
            # Manufacture a synthetic original-free screenshot strip.
            # The X11 edge/panel distances model the captured NeXium frame.
            base=(row*W)*3
            left_b=(first-5)*3
            right_b=(last+1)*3
            screen[base+left_b:base+first*3]=RGB_BORDER*5
            screen[base+first*3:base+(last+1)*3]=RGB_FILL*(last-first+1)
            screen[base+right_b:base+(last+6)*3]=RGB_BORDER*5
            screen[base+(first-6)*3:base+(first-5)*3]=RGB_PANEL
            screen[base+(last+6)*3:base+(last+7)*3]=RGB_PANEL
    return bytes(screen)


def screens():
    return raster(346,928),raster(510,769),raster(None)


class SourceFreeX11ImageTests(unittest.TestCase):
    def test_realistic_nearest_neighbor_road_swatch_pixels(self):
        summary=validate_frames(*screens())
        self.assertEqual(summary["wide_x11_fill_width_px"],583)
        self.assertEqual(summary["narrow_x11_fill_width_px"],260)
        self.assertFalse(summary["original_game_camera_speed_proven"])
        self.assertFalse(summary["original_road_collision_proven"])
    def test_wide_narrow_reversed(self):
        a,b,c=screens()
        with self.assertRaises(ValueError):validate_frames(b,a,c)
    def test_wrong_hd_ratio(self):
        a,_,c=screens()
        with self.assertRaises(ValueError):validate_frames(a,raster(450,849),c)
    def test_wrong_center_shift(self):
        a,_,c=screens()
        with self.assertRaises(ValueError):validate_frames(a,raster(555,814),c)
    def test_missing_measured_fill(self):
        _,b,c=screens()
        with self.assertRaises(ValueError):validate_frames(c,b,c)
    def test_off_does_not_retain_swatch(self):
        a,b,_=screens()
        with self.assertRaises(ValueError):validate_frames(a,b,a)
    def test_short_or_corrupt_rgb_buffer(self):
        a,b,c=screens()
        with self.assertRaises(ValueError):validate_frames(a[:-1],b,c)
    def test_altered_screen_edge_pixel(self):
        a,b,c=screens()
        mutable=bytearray(a)
        y=ROWS[0]
        j=(y*W+345)*3
        mutable[j:j+3]=bytes((1,2,3))
        with self.assertRaises(ValueError):validate_frames(bytes(mutable),b,c)
    def test_disconnected_fill_row(self):
        a,b,c=screens()
        mutable=bytearray(a)
        y=ROWS[2]
        j=(y*W+501)*3
        mutable[j:j+3]=bytes((0,0,0))
        with self.assertRaises(ValueError):validate_frames(bytes(mutable),b,c)


if __name__=="__main__":
    unittest.main()
