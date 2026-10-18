"""Stage134 8x16 synthetic OAM ROM: bank, half, vertical flip controls."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from make_stage134_sprite_8x16_rom import (
    make_rom, MODES, SPRITE16_SETUP,
)
from make_stage129_oam_sprite_rom import explicit_sprite_palette_slot2
from audit_stage132_sprite_flips import flipped_pattern

CHR_START = 16 + 32768


def pattern(image, bank, tile, row, col):
    offset = CHR_START + bank + tile * 16
    low = image[offset + row]
    high = image[offset + 8 + row]
    bit = 7 - col
    return ((low >> bit) & 1) | (((high >> bit) & 1) << 1)


class Synthetic8x16(unittest.TestCase):
    def test_all_modes_and_complete_nonzero_two_tile_patterns(self):
        with tempfile.TemporaryDirectory() as temp:
            images = {}
            for mode in MODES:
                p = Path(temp) / (mode + ".nes")
                make_rom(p, mode)
                images[mode] = p.read_bytes()
            for mode, image in images.items():
                with self.subTest(mode=mode):
                    self.assertEqual(image[:16], b"NES\x1a\x02\x02\x40" + bytes(9))
                    self.assertEqual(len(image), 49168)
                    self.assertEqual(image.count(SPRITE16_SETUP), 4)
                    self.assertEqual(
                        image.count(explicit_sprite_palette_slot2()), 4)
                    for row in range(8):
                        for x in range(8):
                            self.assertEqual(pattern(image, 0, 2, row, x), 2)
                            self.assertEqual(pattern(image, 0, 3, row, x), 1)
                            self.assertEqual(pattern(image, 1024, 2, row, x), 1)
                            self.assertEqual(pattern(image, 1024, 3, row, x), 3)
                            self.assertEqual(pattern(image, 1024, 1, row, x), 3)
            self.assertEqual(len({x[CHR_START:] for x in images.values()}), 1)
            base = images["odd_normal"]
            for mode in MODES[1:]:
                diff = [i for i, (a,b) in enumerate(zip(base,images[mode])) if a!=b]
                self.assertEqual(len(diff), 4 if mode in ("odd_vertical","even_normal") else 8)
                self.assertTrue(all(16 <= i < CHR_START for i in diff))
                self.assertEqual(images[mode][CHR_START:],base[CHR_START:])
                self.assertEqual(len({(i-16)%8192 for i in diff}),
                                 len(diff)//4)

    def test_vertical_flip_swaps_top_and_bottom_bank_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            for mode in MODES:
                path = Path(temp)/(mode+".nes")
                make_rom(path,mode)
                image=path.read_bytes()
                odd=mode.startswith("odd_")
                vertical=mode.endswith("vertical")
                tile=3 if odd else 2
                bank=1024 if odd else 0
                top_expected, bottom_expected=(1,3) if odd else (2,1)
                for y in range(16):
                    row=15-y if vertical else y
                    bank_tile=(tile & ~1) | (row >> 3)
                    expected=top_expected if row < 8 else bottom_expected
                    self.assertEqual(pattern(image,bank,bank_tile,row & 7,0),
                                     expected)
                    # The independent Stage132 model checks the logical
                    # PPU source address, not mapper4's physical ROM offset.
                    low=bytes(255 if
                        (top_expected if r<8 else bottom_expected)&1 else 0
                        for r in range(16))
                    high=bytes(255 if
                        (top_expected if r<8 else bottom_expected)&2 else 0
                        for r in range(16))
                    v,addr=flipped_pattern(
                        tile=tile,x=0,y=y,low=low,high=high,
                        vflip=vertical,height=16)
                    self.assertEqual(v,expected)
                    self.assertEqual(addr, (0x1000 if odd else 0) +
                        bank_tile*16+(row & 7))

    def test_nonexistent_or_ambiguous_modes_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            for mode in ("", "odd", "even", "up", "odd_horizontal", True, None):
                with self.subTest(mode=mode),self.assertRaises(ValueError):
                    make_rom(Path(temp)/"bad.nes",mode)


if __name__ == "__main__":
    unittest.main()
