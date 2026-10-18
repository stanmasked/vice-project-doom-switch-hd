"""Stage128: fail-closed pinned newppu sprite priority source and model tests."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_fceux_stage128_sprite_compositor import (
    SpriteSourceError, verify_sprite_source, compose, ANCHORS,
)

SOURCE = "\n".join(ANCHORS)


class Source(unittest.TestCase):
    def test_source_anchored_sprite_and_bg_contract(self):
        # Earlier renderer has an independent sprite-hit status write.
        report = verify_sprite_source("PPU_status |= 0x40;\n" + SOURCE)
        self.assertTrue(report["priority_source_verified"])
        self.assertFalse(report["native_sprite_pixels_proven"])
        self.assertFalse(report["actual_game_sprites_proven"])

    def test_fail_closed_missing_ambiguous_and_reordered_hooks(self):
        for anchor in ANCHORS:
            with self.subTest(anchor=anchor):
                with self.assertRaises(SpriteSourceError):
                    verify_sprite_source(SOURCE.replace(anchor, "// removed", 1))
        with self.assertRaises(SpriteSourceError):
            verify_sprite_source(SOURCE + "\n" + SOURCE)
        with self.assertRaises(SpriteSourceError):
            verify_sprite_source(
                SOURCE.replace(ANCHORS[7], ANCHORS[7] + "\n" + ANCHORS[7]))
        with self.assertRaises(SpriteSourceError):
            verify_sprite_source(
                SOURCE.replace(ANCHORS[7], "// temporarily") + "\n" + ANCHORS[7])
        with self.assertRaises(SpriteSourceError):
            verify_sprite_source(b"")
        with self.assertRaises(SpriteSourceError):
            verify_sprite_source(10)


class IndependentModel(unittest.TestCase):
    def test_32_combinations_of_bg_sprite_and_priority(self):
        for bg in range(4):
            for sp in range(4):
                for behind in (False, True):
                    with self.subTest(bg=bg, sp=sp, behind=behind):
                        result = compose(bg, 2, sp, 1, behind=behind)
                        visible = sp > 0 and (not behind or bg == 0)
                        self.assertEqual(result["sprite_visible"], visible)
                        self.assertEqual(result["sprite0_hit"], bg > 0 and sp > 0)
                        self.assertEqual(result["palette_index"],
                                         0x10 + sp + 4 if visible else bg + 8)

    def test_sprite0_hit_independent_of_sprite_priority(self):
        self.assertEqual(compose(3, 0, 2, 1, behind=True),
                         {"palette_index": 3, "sprite_visible": False,
                          "sprite0_hit": True})
        self.assertFalse(compose(3, 0, 2, 1, x=255)["sprite0_hit"])
        self.assertFalse(compose(3, 0, 0, 1)["sprite0_hit"])
        self.assertFalse(compose(0, 0, 2, 1)["sprite0_hit"])
        self.assertFalse(compose(3, 0, 2, 1, sprite_zero=False)["sprite0_hit"])
        self.assertFalse(compose(3, 0, 2, 1, sprite_enabled=False)["sprite0_hit"])
        self.assertFalse(compose(3, 0, 2, 1, bg_enabled=False)["sprite0_hit"])

    def test_bad_parameters_refused(self):
        for value in (-1, 4, True, 1.0, "2"):
            with self.subTest(value=value), self.assertRaises(SpriteSourceError):
                compose(value, 0, 1, 0)
        for x in (-1, 256, True):
            with self.assertRaises(SpriteSourceError):
                compose(1, 0, 1, 0, x=x)
        with self.assertRaises(SpriteSourceError):
            compose(1, 0, 1, 0, behind=1)


if __name__ == "__main__":
    unittest.main()
