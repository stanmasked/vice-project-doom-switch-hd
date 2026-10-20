#!/usr/bin/env python3
"""Adversarial ROM-free 1280x720 X11 tests for the actual hero impact flash."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_nexium_sentry_hero_impact import hero_impact_pixels

WIDTH, HEIGHT = 1280, 720
CHEST = (255, 220, 153)
HEAD = (252, 180, 119)

def block(frame, x0, x1, y0, y1, color):
    ink = bytes(color)
    for y in range(y0, y1):
        for x in range(x0, x1):
            p = 3 * (y * WIDTH + x)
            frame[p:p+3] = ink

def pair():
    before = bytearray(WIDTH * HEIGHT * 3)
    block(before, 339, 366, 580, 592, (164, 51, 68))
    block(before, 345, 368, 560, 572, (220, 179, 137))
    after = bytearray(before)
    block(after, 335, 357, 574, 578, CHEST)
    block(after, 332, 358, 554, 556, HEAD)
    return before, after

class HeroImpactX11Test(unittest.TestCase):
    def test_two_stripes_preserve_the_original_actor(self):
        before, after = pair()
        self.assertEqual(hero_impact_pixels(before, after), (88, 52, 324, 276))

    def test_reject_hud_only_flash(self):
        before, after = pair()
        block(after, 335, 357, 574, 578, (0, 0, 0))
        block(after, 332, 358, 554, 556, (0, 0, 0))
        block(after, 760, 782, 17, 21, CHEST)
        with self.assertRaisesRegex(ValueError, "both independent"):
            hero_impact_pixels(before, after)

    def test_reject_only_one_hero_stripe(self):
        before, after = pair()
        block(after, 332, 358, 554, 556, (0, 0, 0))
        with self.assertRaisesRegex(ValueError, "both independent"):
            hero_impact_pixels(before, after)

    def test_reject_flash_already_present_before_hit(self):
        before, after = pair()
        block(before, 335, 357, 574, 578, CHEST)
        with self.assertRaisesRegex(ValueError, "already present"):
            hero_impact_pixels(before, after)

    def test_reject_flash_painted_away_from_hero(self):
        before, after = pair()
        block(after, 335, 357, 574, 578, (0, 0, 0))
        block(after, 332, 358, 554, 556, (0, 0, 0))
        block(after, 395, 417, 574, 578, CHEST)
        block(after, 392, 418, 554, 556, HEAD)
        with self.assertRaisesRegex(ValueError, "shape/location"):
            hero_impact_pixels(before, after)

    def test_reject_actor_removed_after_hit(self):
        before, after = pair()
        block(after, 339, 366, 580, 592, (0, 0, 0))
        with self.assertRaisesRegex(ValueError, "same original hero"):
            hero_impact_pixels(before, after)

    def test_reject_broken_stripe_despite_sufficient_pixel_count(self):
        before, after = pair()
        # 84/88 pixels survive, but one stripe row is no longer contiguous.
        for x in (343, 344, 345, 346):
            p = 3 * (574 * WIDTH + x)
            after[p:p+3] = b"\x00\x00\x00"
        with self.assertRaisesRegex(ValueError, "broken rows"):
            hero_impact_pixels(before, after)

    def test_reject_truncated_native_x11_frame(self):
        before, after = pair()
        with self.assertRaisesRegex(ValueError, "1280x720"):
            hero_impact_pixels(before[:2000], after)

if __name__ == "__main__":
    unittest.main()
