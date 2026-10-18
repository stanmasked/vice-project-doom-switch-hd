"""Stage130 OAM-order source guards and two overlapping sprite regressions."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_stage130_two_sprite_order import (
    Sprite, compose, verify_source, OverlapError, ANCHORS,
)


class TwoSpriteOAM(unittest.TestCase):
    def test_front_and_reversed_oam(self):
        a = compose(3, 0, [Sprite(0, 3, 0), Sprite(1, 3, 1)])
        b = compose(3, 0, [Sprite(0, 3, 1), Sprite(1, 3, 0)])
        self.assertEqual((a["xbuf"], b["xbuf"]), (170, 184))
        self.assertEqual((a["drawn_oam"], b["drawn_oam"]), (0, 0))
        self.assertTrue(a["sprite0_hit"])
        self.assertTrue(b["sprite0_hit"])
        self.assertFalse(a["native_two_sprite_pixels_proven"])

    def test_first_transparent_second_visible(self):
        r = compose(3, 0, [Sprite(0, 0, 0), Sprite(1, 3, 1)])
        self.assertEqual(r["xbuf"], 184)
        self.assertEqual(r["drawn_oam"], 1)
        self.assertFalse(r["sprite0_hit"])

    def test_behind_opaque_claim_blocks_next_sprite(self):
        r = compose(3, 0, [Sprite(0, 3, 0, True), Sprite(1, 3, 1)])
        self.assertEqual(
            (r["xbuf"], r["drawn_oam"], r["claimed_oam"]),
            (176, None, 0))
        self.assertTrue(r["sprite0_hit"])

    def test_behind_transparent_bg_visible_no_hit(self):
        r = compose(0, 0, [Sprite(0, 3, 0, True), Sprite(1, 3, 1)])
        self.assertEqual(r["xbuf"], 170)
        self.assertFalse(r["sprite0_hit"])

    def test_disabled_sprite_and_last_pixel_hit(self):
        pair = [Sprite(0, 3, 0), Sprite(1, 3, 1)]
        self.assertFalse(compose(3, 0, pair, x=255)["sprite0_hit"])
        self.assertEqual(
            compose(3, 0, pair, sprite_enabled=False)["xbuf"], 176)

    def test_oam_guards_and_source_order(self):
        for bad in (None, [], [Sprite(1, 3, 0), Sprite(0, 3, 1)],
                    [Sprite(0, 3, 0), Sprite(1, True, 1)],
                    [Sprite(0, 3, 0), Sprite(1, 3, 0, 1)]):
            with self.subTest(bad=bad), self.assertRaises(OverlapError):
                compose(3, 0, bad)
        good = "\n".join(ANCHORS) + "\n*ptr = PaletteAdjustPixel(pixelcolor);"
        self.assertTrue(verify_source(good)["two_sprite_source_order_verified"])
        self.assertFalse(verify_source(good)["native_two_sprite_pixels_proven"])
        for anchor in ANCHORS:
            with self.subTest(anchor=anchor), self.assertRaises(OverlapError):
                verify_source(good.replace(anchor, "removed", 1))
        for corrupt in (good + "\n" + good, 5):
            with self.assertRaises(OverlapError):
                verify_source(corrupt)


if __name__ == "__main__":
    unittest.main()
