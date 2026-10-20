#!/usr/bin/env python3
"""Adversarial source-derived genuine X11 guard READY ! proof."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_nexium_guard_ready_x11 import verify_ready_raster, source_ready_x

W,H=1280,720
GX,GY=480,559
SOURCE_X=480
SRC=(
    b"VPD_ROMFREE_GUARD_LIVE_V1 seq=1 event=alert frame=143 "
    b"player_x=25600 guard_x=61696 player_hp=5 guard_hp=2 "
    b"attacks=0 cooldown=0 alerted=1 input_right=1 source=live_guest "
    b"original_game_proven=no\n"
    b"VPD_ROMFREE_GUARD_LIVE_V1 seq=2 event=strike frame=195 "
    b"player_x=52224 guard_x=57344 player_hp=4 guard_hp=2 "
    b"attacks=1 cooldown=32 alerted=1 input_right=1 source=live_guest "
    b"original_game_proven=no\n"
)


def rectangle(a,x0,x1,y0,y1,rgb):
    ink=bytes(rgb)
    for y in range(y0,y1):
        for x in range(x0,x1):
            offset=(y*W+x)*3
            a[offset:offset+3]=ink


def screenshot(ready):
    a=bytearray(W*H*3)
    for x in (GX+2,GX+10):
        rectangle(a,x,x+6,GY-7,GY-4,(247,175,96))
    rectangle(a,GX+3,GX+21,GY+3,GY+11,(65,76,94))
    rectangle(a,GX+10,GX+20,GY+4,GY+9,(194,110,92))
    if ready:
        rectangle(a,GX+10,GX+16,GY-27,GY-16,(248,198,104))
        rectangle(a,GX+10,GX+16,GY-13,GY-9,(248,198,104))
    else:
        for n in range(3):
            rectangle(a,GX+5+n*8,GX+11+n*8,GY-22,GY-18,
                      (92,101,118))
    return a


def ppm(buf):
    return b"P6\n1280 720\n255\n"+bytes(buf)


class ReadyRasterTests(unittest.TestCase):
    def test_authentic_ready_exclamation_and_replacement(self):
        d=verify_ready_raster(ppm(screenshot(True)),
                              ppm(screenshot(False)),SOURCE_X)
        self.assertEqual((d["stem_pixels"],d["dot_pixels"],
                          d["strike_dim_pixels"]),(66,24,72))

    def test_source_first_alert_authoritative_and_in_view(self):
        self.assertEqual(source_ready_x(SRC),482)

    def test_source_rejects_forged_health_or_attack_cooldown(self):
        for old,new in ((b"cooldown=0",b"cooldown=32"),
                        (b"player_hp=5",b"player_hp=4"),
                        (b"guard_hp=2",b"guard_hp=0"),
                        (b"alerted=1",b"alerted=0"),
                        (b"input_right=1",b"input_right=0")):
            with self.subTest(change=new),self.assertRaises(ValueError):
                source_ready_x(SRC.replace(old,new,1))

    def test_reject_ready_without_stem(self):
        a=screenshot(True)
        rectangle(a,GX+10,GX+16,GY-27,GY-16,(0,0,0))
        with self.assertRaisesRegex(ValueError,"stem or dot"):
            verify_ready_raster(ppm(a),ppm(screenshot(False)),SOURCE_X)

    def test_reject_ready_without_dot(self):
        a=screenshot(True)
        rectangle(a,GX+10,GX+16,GY-13,GY-9,(0,0,0))
        with self.assertRaisesRegex(ValueError,"stem or dot"):
            verify_ready_raster(ppm(a),ppm(screenshot(False)),SOURCE_X)

    def test_reject_cooldown_pips_visible_during_ready(self):
        a=screenshot(True)
        # Do NOT paint all three bars over the amber center stem:
        # doing so makes the independent missing-! test reject first,
        # without ever testing the contradictory live cooldown bars.
        # Real hostile fixture: two dim bars remain visible outside
        # the intact original READY glyph.
        for n in (0,2):
            rectangle(a,GX+5+n*8,GX+11+n*8,GY-22,GY-18,
                      (92,101,118))
        with self.assertRaisesRegex(ValueError,"already on cooldown"):
            verify_ready_raster(ppm(a),ppm(screenshot(False)),SOURCE_X)

    def test_reject_ready_icon_persists_after_hit(self):
        b=screenshot(False)
        rectangle(b,GX+10,GX+16,GY-27,GY-16,(248,198,104))
        with self.assertRaisesRegex(ValueError,"still visible"):
            verify_ready_raster(ppm(screenshot(True)),ppm(b),SOURCE_X)

    def test_reject_unanchored_icon(self):
        with self.assertRaisesRegex(ValueError,"sprite"):
            verify_ready_raster(ppm(screenshot(True)),
                                ppm(screenshot(False)),850)

    def test_reject_not_enough_strike_pips(self):
        b=screenshot(False)
        rectangle(b,GX+21,GX+27,GY-22,GY-18,(0,0,0))
        with self.assertRaisesRegex(ValueError,"cooldown pips"):
            verify_ready_raster(ppm(screenshot(True)),ppm(b),SOURCE_X)

    def test_reject_malformed_original_x11_p6(self):
        with self.assertRaises(ValueError):
            verify_ready_raster(ppm(screenshot(True))[:-1],
                                ppm(screenshot(False)),SOURCE_X)


if __name__=="__main__":
    unittest.main()
