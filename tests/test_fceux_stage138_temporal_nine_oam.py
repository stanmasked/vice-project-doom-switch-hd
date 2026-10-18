"""Stage138 temporal nine-sprite 8x16 synthetic ROM and OAM member regressions."""
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))

from make_stage138_temporal_oam_rom import (
    MODES,UPPER_ROW,LOWER_ROW,slots,expected,oam_setup,make_rom)
from make_stage137_nine_sprite_rom import OAM_CLEAR,SPRITE16_SETUP


class TemporalNineOAM(unittest.TestCase):
    def test_first_eight_stable_across_both_halves(self):
        r=expected("eight_stable")
        for row in ("upper","lower"):
            self.assertEqual(r[row]["chosen_oam_indexes"],tuple(range(8)))
            self.assertEqual(r[row]["selected_count"],8)
            self.assertFalse(r[row]["sprite_overflow_bit"])
        self.assertEqual((r["xbuf_upper"],r["xbuf_lower"]),(143,143))

    def test_ninth_enters_lower_half_only_and_is_suppressed(self):
        r=expected("nine_late")
        for row in ("upper","lower"):
            self.assertEqual(r[row]["chosen_oam_indexes"],tuple(range(8)))
        self.assertFalse(r["upper"]["sprite_overflow_bit"])
        self.assertTrue(r["lower"]["sprite_overflow_bit"])
        self.assertEqual((r["xbuf_upper"],r["xbuf_lower"]),(143,143))
        self.assertEqual((UPPER_ROW,LOWER_ROW),(124,132))

    def test_one_free_slot_allows_eighth_selected_late_sprite(self):
        r=expected("seven_plus_late")
        self.assertEqual(r["upper"]["chosen_oam_indexes"],tuple(range(7)))
        self.assertEqual(r["lower"]["chosen_oam_indexes"],
                         tuple(range(7))+(8,))
        self.assertFalse(r["upper"]["sprite_overflow_bit"])
        self.assertFalse(r["lower"]["sprite_overflow_bit"])
        self.assertEqual((r["xbuf_upper"],r["xbuf_lower"]),(143,170))

    def test_ninth_early_overflows_across_two_scanlines(self):
        r=expected("nine_early")
        self.assertTrue(r["upper"]["sprite_overflow_bit"])
        self.assertTrue(r["lower"]["sprite_overflow_bit"])
        self.assertEqual(r["upper"]["chosen_oam_indexes"],tuple(range(8)))
        self.assertEqual(r["lower"]["chosen_oam_indexes"],tuple(range(8)))
        self.assertEqual((r["xbuf_upper"],r["xbuf_lower"]),(143,143))

    def test_all_roms_single_chr_and_correct_banked_oam_sequence(self):
        with tempfile.TemporaryDirectory() as td:
            images={}
            for mode in MODES:
                dest=Path(td)/(mode+".nes")
                make_rom(dest,mode)
                images[mode]=dest.read_bytes()
            self.assertEqual(len({x[-16384:] for x in images.values()}),1)
            for mode,image in images.items():
                with self.subTest(mode=mode):
                    self.assertEqual(image[:16],
                                     b"NES\x1a\x02\x02\x40"+bytes(9))
                    self.assertEqual(len(image),49168)
                    self.assertEqual(len(slots(mode)),64)
                    self.assertTrue(all(y==255 for y in slots(mode)[9:]))
                    init=oam_setup(mode)
                    self.assertEqual(len(init),len(OAM_CLEAR)+9*4*5)
                    self.assertTrue(init.startswith(OAM_CLEAR))
                    self.assertEqual(image[16:16+32768].count(init),4)
                    self.assertEqual(image[16:16+32768].count(SPRITE16_SETUP),4)
                    self.assertEqual(image[-16384+1024+16:-16384+1024+32],
                                     bytes(16))
                    self.assertEqual(image[-16384+1024+32:-16384+1024+64],
                                     bytes((255,))*32)
                    self.assertEqual(image[-16384:][:32],bytes(32))
            before=images["nine_late"]
            for mode,image in images.items():
                differences=[i for i,(a,b) in enumerate(zip(before,image))
                             if a!=b]
                self.assertTrue(all(16<=i<16+32768 for i in differences))
                self.assertLessEqual(len(differences),8)

    def test_invalid_modes_do_not_create_roms(self):
        with tempfile.TemporaryDirectory() as td:
            for bad in ("","unknown","stage137",None,True,17):
                with self.subTest(bad=bad):
                    p=Path(td)/"bad.nes"
                    with self.assertRaises(ValueError):
                        make_rom(p,bad)
                    self.assertFalse(p.exists())
                    with self.assertRaises(ValueError):
                        slots(bad)


if __name__=="__main__":
    unittest.main()
