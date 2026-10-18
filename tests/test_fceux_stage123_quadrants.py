"""Stage123 ROM-free four-quadrant palette preflight and negative controls."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_stage123_quadrant_palette import (
    ATTRIBUTE_BYTE, PALETTE_RAM, QuadrantEvidenceError, source,
    attr_addr, attr_shift, decode, audit_four_quadrants,
)


class Quadrants(unittest.TestCase):
    def test_four_groups_and_palette_colors_across_four_pages(self):
        result = audit_four_quadrants()
        self.assertEqual(result["observed_pixel_indices"], [3, 7, 11, 15])
        self.assertFalse(result["native_fceux_palette_proven"])
        self.assertFalse(result["original_game_palette_proven"])
        for page in range(4):
            samples = [decode(source(x, y, page), ATTRIBUTE_BYTE, 3)
                       for x, y in ((0, 0), (2, 0), (0, 2), (2, 2))]
            self.assertEqual([s["group"] for s in samples], [0, 1, 2, 3])
            self.assertEqual(len({s["attribute_address"] for s in samples}), 1)
            self.assertEqual(samples[0]["attribute_address"], 0x23C0 + page * 0x400)
            self.assertEqual(
                [s["palette_color"] for s in samples], [0x30, 0x31, 0x32, 0x33])

    def test_attribute_math_and_quadrant_shift(self):
        self.assertEqual(attr_addr(source(31, 29, 3)), 0x2FFF)
        self.assertEqual(attr_addr(source(4, 4)), 0x23C9)
        self.assertEqual(
            [attr_shift(source(x, y)) for x, y in
             ((0, 0), (2, 0), (0, 2), (2, 2))], [0, 2, 4, 6])

    def test_attribute_byte_and_palette_mutations_fail_closed(self):
        for value in (0, 0x55, 0x1B, 0xF4, 0xD8):
            with self.subTest(value=value), self.assertRaises(QuadrantEvidenceError):
                audit_four_quadrants(value)
        for index in (3, 7, 11, 15):
            palette = list(PALETTE_RAM)
            palette[index] = PALETTE_RAM[7 if index == 3 else 3]
            with self.subTest(index=index), self.assertRaises(QuadrantEvidenceError):
                audit_four_quadrants(palette=tuple(palette))

    def test_invalid_coordinate_and_byte_values_fail_closed(self):
        for x, y, page in (
                (-1, 0, 0), (32, 0, 0), (0, 30, 0), (0, -1, 0),
                (0, 0, 4), (True, 0, 0), (2.0, 0, 0)):
            with self.subTest(coords=(x, y, page)), self.assertRaises(QuadrantEvidenceError):
                source(x, y, page)
        for addr in (-1, 0x1FFF, 0x3000, True, "2000"):
            with self.subTest(address=addr), self.assertRaises(QuadrantEvidenceError):
                attr_addr(addr)
            with self.assertRaises(QuadrantEvidenceError):
                attr_shift(addr)
        for attribute, pattern in (
                (256, 3), (-1, 3), (0xE4, 0), (0xE4, 4),
                (True, 3), (0xE4, 1.0)):
            with self.subTest(pair=(attribute, pattern)), self.assertRaises(QuadrantEvidenceError):
                decode(0x2000, attribute, pattern)


if __name__ == "__main__":
    unittest.main()
