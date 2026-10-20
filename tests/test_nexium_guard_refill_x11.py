#!/usr/bin/env python3
"""Negative tests for real-source guard cooldown 32->20 and native X11 pips."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_nexium_guard_refill_x11 import witness,verify_refill_raster,verify_prior_strike_receipts

W,H=1280,720
GX,GY=370,559
SOURCE_X=360
VALID=(
    b"VPD_GUARD_COOLDOWN_REFILL_V1 strike_frame=177 frame=189 "
    b"hero_x=52224 guard_x=57344 camera_x=44 "
    b"hero_hp=4 guard_hp=2 attacks=1 cooldown=20 "
    b"input=idle hd=on source=libnx_tick original_game_proven=no\n"
)
EVENTS={"alert_frame":131,"strike_frame":177}


def box(im,x0,x1,y0,y1,color):
    raw=bytes(color)
    for y in range(y0,y1):
        for x in range(x0,x1):
            p=3*(y*W+x)
            im[p:p+3]=raw


def sample(refilled=False):
    im=bytearray(W*H*3)
    # Unique four independent actual source guard HP/body anchor colors.
    for x,rgb,y in (
        (GX+2,(247,175,96),GY-7),
        (GX+10,(247,175,96),GY-7),
        (GX+3,(65,76,94),GY+3),
        (GX+10,(194,110,92),GY+4),
    ):
        box(im,x,x+1,y,y+1,rgb)
    for n in range(3):
        rgb=(237,170,101) if refilled and n==0 else (92,101,118)
        box(im,GX+5+8*n,GX+11+8*n,GY-22,GY-18,rgb)
    return im


def ppm(im):
    return b"P6\n1280 720\n255\n"+bytes(im)


class NativeRefillTest(unittest.TestCase):
    def test_real_guest_idle_source_event(self):
        self.assertEqual(witness(VALID,EVENTS)["frame"],189)

    def test_reject_forged_timing_and_health(self):
        for before,after in (
            (b"frame=189",b"frame=190"),
            (b"strike_frame=177",b"strike_frame=176"),
            (b"hero_hp=4",b"hero_hp=5"),
            (b"guard_hp=2",b"guard_hp=0"),
            (b"cooldown=20",b"cooldown=32"),
            (b"attacks=1",b"attacks=0"),
            (b"input=idle",b"input=right"),
            (b"source=libnx_tick",b"source=host"),
        ):
            with self.subTest(after=after),self.assertRaises(ValueError):
                witness(VALID.replace(before,after),EVENTS)

    def test_reject_duplicate_or_truncated_real_guest_witness(self):
        for blob in (VALID*2,VALID[:-1],b"",b"garbage"):
            with self.assertRaises(ValueError):
                witness(blob,EVENTS)

    def test_real_one_lit_two_dim_source_pixels(self):
        d=verify_refill_raster(ppm(sample(False)),ppm(sample(True)),SOURCE_X)
        self.assertEqual((d["warm"],d["dim"],d["gx"]),(24,48,GX))

    def test_real_nexium_x11_native_shift_reproduces_18_15_15_pixels(self):
        # Measured from actual P6 frame in run #39496177544, anchored
        # to the original living guard at (370,559). The three displayed
        # rectangles occupy y=538..541, while the bounded strict audit
        # samples y=537..540. Thus 3 scanned rows: warm 6*3=18,
        # and each native five-wide dim bar 5*3=15 (not 24/15/15).
        frame=sample(True)
        for base in (GX+5,GX+13,GX+21):
            box(frame,base,base+6,GY-22,GY-18,(0,0,0))
        for index,base in enumerate((GX+5,GX+13,GX+21)):
            width=6 if index==0 else 5
            color=(237,170,101) if index==0 else (92,101,118)
            box(frame,base,base+width,GY-21,GY-17,color)
        result=verify_refill_raster(
            ppm(sample(False)),ppm(frame),SOURCE_X)
        self.assertEqual((result["warm"],result["dim"]), (18,30))

    def test_reject_dim_pip_below_native_measured_coverage(self):
        frame=sample(True)
        # The genuine X11 dim cells have 15 pixels, but a fragment with
        # 13 must not qualify as one of the two correctly dim pips.
        box(frame,GX+13,GX+19,GY-22,GY-21,(42,56,75))
        box(frame,GX+13,GX+18,GY-21,GY-20,(42,56,75))
        with self.assertRaisesRegex(ValueError,"one pip"):
            verify_refill_raster(
                ppm(sample(False)),ppm(frame),SOURCE_X)

    def test_reject_no_refill(self):
        with self.assertRaisesRegex(ValueError,"one pip"):
            verify_refill_raster(
                ppm(sample(True)),ppm(sample(False)),SOURCE_X)

    def test_reject_two_pips_lit_early(self):
        new=sample(True)
        box(new,GX+13,GX+19,GY-22,GY-18,(237,170,101))
        with self.assertRaisesRegex(ValueError,"one pip"):
            verify_refill_raster(ppm(sample(False)),ppm(new),SOURCE_X)

    def test_reject_ready_exclamation_during_real_cooldown(self):
        new=sample(True)
        # Put the spurious READY stem strictly ABOVE the three pips;
        # painting through the second dim pip would trigger the separate
        # "one pip" guard first and leave this negative test ineffective.
        box(new,GX+10,GX+15,GY-27,GY-23,(248,198,104))
        with self.assertRaisesRegex(ValueError,"READY"):
            verify_refill_raster(ppm(sample(False)),ppm(new),SOURCE_X)

    def test_reject_unanchored_forged_cooldown_pips(self):
        with self.assertRaisesRegex(ValueError,"sprite"):
            verify_refill_raster(ppm(sample(False)),ppm(sample(True)),780)

    def test_prior_real_x11_receipts_same_strike(self):
        sha="a"*64
        cool=("VPD_NEXIUM_GUARD_COOLDOWN_X11_PASS "
              "alert_frame=131 strike_frame=177 defeat_frame=199 "
              "strike_ppm_sha256="+sha+" source=live_guest\\n")
        ready=("VPD_NEXIUM_GUARD_READY_X11_PASS "
               "alert_frame=131 strike_frame=177 source_guard_hp=2 "
               "strike_ppm_sha256="+sha+" source=live_guest\\n")
        self.assertTrue(verify_prior_strike_receipts(cool,ready,177,sha))

    def test_reject_foreign_strike_receipts_and_replays(self):
        sha="a"*64
        cool=("VPD_NEXIUM_GUARD_COOLDOWN_X11_PASS "
              "alert_frame=131 strike_frame=177 "
              "strike_ppm_sha256="+sha+" source=live_guest\\n")
        ready=("VPD_NEXIUM_GUARD_READY_X11_PASS "
               "alert_frame=131 strike_frame=177 "
               "strike_ppm_sha256="+sha+" source=live_guest\\n")
        for bad_cool,bad_ready in (
            (cool.replace("strike_frame=177","strike_frame=178"),ready),
            (cool,ready.replace("strike_frame=177","strike_frame=178")),
            (cool.replace(sha,"b"*64),ready),
            (cool,ready.replace(sha,"b"*64)),
            (cool,ready+ready),
            (cool.replace("VPD_NEXIUM_GUARD_COOLDOWN_X11_PASS ",
                          "unverified "),ready),
            (cool,ready.replace("strike_ppm_sha256=","fake_sha256=")),
        ):
            with self.subTest(forgery=bad_cool[:30]),self.assertRaises(ValueError):
                verify_prior_strike_receipts(bad_cool,bad_ready,177,sha)

    def test_reject_stale_or_replayed_x11(self):
        src=ppm(sample(True))
        with self.assertRaisesRegex(ValueError,"identical"):
            verify_refill_raster(src,src,SOURCE_X)

    def test_reject_native_raster_truncation(self):
        with self.assertRaises(ValueError):
            verify_refill_raster(ppm(sample(False)),ppm(sample(True))[:-1],SOURCE_X)

if __name__=="__main__":
    unittest.main()
