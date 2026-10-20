#!/usr/bin/env python3
"""Adversarial guard cooldown/source X11 pixel provenance regressions."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_nexium_guard_cooldown_x11 import (
    verify_cooldown_raster, guard_sprite_anchor
)

WIDTH, HEIGHT=1280,720
GX,GY=370,559
ANCHORS={"strike_x":360,"defeat_x":360}


def ink(buffer,x,y,c):
    ix=(y*WIDTH+x)*3
    buffer[ix:ix+3]=bytes(c)

def scene(with_pips=True):
    a=bytearray(WIDTH*HEIGHT*3)
    orange=(247,175,96)
    base=(65,76,94)
    face=(194,110,92)
    for x in (GX+2,GX+10):
        ink(a,x,GY-7,orange)
    ink(a,GX+3,GY+3,base)
    ink(a,GX+10,GY+4,face)
    if with_pips:
        for n in range(3):
            for y in range(GY-22,GY-18):
                for x in range(GX+5+8*n,GX+11+8*n):
                    ink(a,x,y,(92,101,118))
    return a

def ppm(pixels):
    return b"P6\n1280 720\n255\n"+bytes(pixels)

class TestGuardNativeCooldown(unittest.TestCase):
    def test_true_guard_sprite_anchor_and_dim_cooldown(self):
        before=ppm(scene())
        after=ppm(bytearray(WIDTH*HEIGHT*3))
        result=verify_cooldown_raster(before,after,ANCHORS)
        self.assertEqual(result["source_guard_x11"],GX)
        self.assertEqual(result["cooldown_dim_pixels"],72)
        self.assertEqual(result["post_defeat_dim_pixels"],0)

    def test_reject_absent_guard_sprite(self):
        with self.assertRaisesRegex(ValueError,"sprite"):
            guard_sprite_anchor(bytearray(WIDTH*HEIGHT*3),360)

    def test_reject_not_enough_real_dim_pips(self):
        on=scene()
        for x in range(GX+21,GX+27):
            for y in range(GY-22,GY-18):
                ink(on,x,y,(42,56,75))
        with self.assertRaisesRegex(ValueError,"dim"):
            verify_cooldown_raster(ppm(on),ppm(bytearray(WIDTH*HEIGHT*3)),ANCHORS)

    def test_reject_ready_exclamation_when_melee_on_cooldown(self):
        on=scene()
        ink(on,GX+10,GY-27,(248,198,104))
        with self.assertRaisesRegex(ValueError,"attack-ready"):
            verify_cooldown_raster(ppm(on),ppm(bytearray(WIDTH*HEIGHT*3)),ANCHORS)

    def test_reject_pips_still_visible_after_guard_kill(self):
        ghost=scene()
        ink(ghost,GX+3,GY+3,(0,0,0))
        with self.assertRaisesRegex(ValueError,"persisted"):
            verify_cooldown_raster(ppm(scene()),ppm(ghost),ANCHORS)

    def test_reject_health_color_fake_and_unanchored_three_bars(self):
        on=scene()
        ink(on,GX+10,GY-7,(0,0,0))
        with self.assertRaisesRegex(ValueError,"sprite"):
            verify_cooldown_raster(ppm(on),ppm(bytearray(WIDTH*HEIGHT*3)),ANCHORS)

    def test_reject_cam_tampered_source_anchor(self):
        with self.assertRaisesRegex(ValueError,"sprite"):
            verify_cooldown_raster(ppm(scene()),ppm(bytearray(WIDTH*HEIGHT*3)),
                                   {"strike_x":850,"defeat_x":360})

    def test_reject_not_full_native_ppm(self):
        with self.assertRaises(ValueError):
            verify_cooldown_raster(ppm(scene())[:-1],
                                   ppm(bytearray(WIDTH*HEIGHT*3)),ANCHORS)

    def test_reject_same_frame_reused_for_defeat(self):
        a=ppm(scene())
        with self.assertRaisesRegex(ValueError,"single X11 frame"):
            verify_cooldown_raster(a,a,ANCHORS)

if __name__=="__main__":
    unittest.main()
