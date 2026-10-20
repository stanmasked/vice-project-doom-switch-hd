#!/usr/bin/env python3
"""Adversarial ROM-free tests: genuine 16-tick expiry + three native X11 frames."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_nexium_sentry_hero_recovery import (
    verify_recovery, recovered_actor_pixels,
)

WIDTH, HEIGHT = 1280, 720
HIT = dict(frame=400, hero_hp_after=4, hero_x=119808, hero_y=55000,
           shots_hit_after=1)
TEAL = (106, 198, 174)
EMPTY = (55, 64, 79)
YELLOW = (255, 220, 153)

def record(*, first=400, last=416, old=4, new=4,
           x=119808, y=55000, hits=1):
    return (
        f"VPD_HD_FX_SENTRY_RECOVER_V1 hit_frame={first} frame={last} "
        f"flash_before=1 flash_after=0 hero_hp_before={old} hero_hp_after={new} "
        f"hero_x={x} hero_y={y} shots_hit={hits} "
        "mode=on input=idle wave=1 guard_hp=0 sentry_hp=2 "
        "source=libnx_tick original_game_proven=no\n"
    ).encode("ascii")

def block(img, left, right, top, bottom, rgb):
    ink = bytes(rgb)
    for y in range(top, bottom):
        for x in range(left, right):
            i = (y * WIDTH + x) * 3
            img[i:i+3] = ink

def frames():
    before = bytearray(WIDTH * HEIGHT * 3)
    block(before, 339, 366, 580, 592, (164, 51, 68))
    block(before, 345, 368, 560, 572, (220, 179, 137))
    for left, right in ((757, 766), (771, 781), (786, 795),
                        (800, 810), (814, 825)):
        block(before, left, right, 17, 29, TEAL)
    impact = bytearray(before)
    for left, right in ((757, 766), (771, 781), (786, 795), (800, 810)):
        block(impact, left, right, 17, 29, YELLOW)
    block(impact, 814, 825, 17, 29, EMPTY)
    block(impact, 335, 357, 574, 578, YELLOW)
    block(impact, 332, 358, 554, 556, (252, 180, 119))
    recovered = bytearray(before)
    block(recovered, 814, 825, 17, 29, EMPTY)
    return before, impact, recovered

class RecoverySourceTest(unittest.TestCase):
    def test_one_exact_source_tick_expiry(self):
        self.assertEqual(verify_recovery(record(), HIT)["frame"], 416)

    def test_reject_forged_or_unrelated_expiry(self):
        changes = [
            dict(first=399), dict(last=415), dict(last=417),
            dict(old=5), dict(new=5), dict(new=3),
            dict(x=119809), dict(y=55001), dict(hits=2),
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                verify_recovery(record(**change), HIT)
        for a, b in (
            (b"input=idle", b"input=right"),
            (b"flash_after=0", b"flash_after=1"),
            (b"source=libnx_tick", b"source=host"),
            (b"original_game_proven=no", b"original_game_proven=yes"),
        ):
            with self.subTest(b=b), self.assertRaises(ValueError):
                verify_recovery(record().replace(a, b), HIT)
        for raw in (record()[:-1], record()*2, b"\xff"):
            with self.assertRaises(ValueError):
                verify_recovery(raw, HIT)

class RecoveryX11Test(unittest.TestCase):
    def test_hero_flash_expires_but_fifth_heart_stays_empty(self):
        before, impact, recovered = frames()
        fifth, jacket, face = recovered_actor_pixels(before, impact, recovered)
        self.assertEqual(fifth, 132)
        self.assertEqual((jacket, face), (324, 276))

    def test_reject_flash_still_present_after_expiry(self):
        before, impact, recovered = frames()
        block(recovered, 335, 357, 574, 578, YELLOW)
        with self.assertRaisesRegex(ValueError, "remains visible"):
            recovered_actor_pixels(before, impact, recovered)

    def test_reject_hero_missing_from_recovered_image(self):
        before, impact, recovered = frames()
        block(recovered, 339, 366, 580, 592, (0, 0, 0))
        with self.assertRaisesRegex(ValueError, "actor no longer"):
            recovered_actor_pixels(before, impact, recovered)

    def test_reject_health_restored_without_source(self):
        before, impact, recovered = frames()
        block(recovered, 814, 825, 17, 29, TEAL)
        with self.assertRaises(ValueError):
            recovered_actor_pixels(before, impact, recovered)

    def test_reject_second_heart_lost_during_recovery(self):
        before, impact, recovered = frames()
        block(recovered, 773, 776, 20, 23, EMPTY)
        with self.assertRaises(ValueError):
            recovered_actor_pixels(before, impact, recovered)

    def test_reject_flash_that_never_happened(self):
        before, impact, recovered = frames()
        block(impact, 335, 357, 574, 578, (0, 0, 0))
        with self.assertRaises(ValueError):
            recovered_actor_pixels(before, impact, recovered)

    def test_reject_truncated_presentation(self):
        before, impact, recovered = frames()
        with self.assertRaises(ValueError):
            recovered_actor_pixels(before, impact[:500], recovered)

if __name__ == "__main__":
    unittest.main()
