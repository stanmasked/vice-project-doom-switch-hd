"""Stage136 eight-slot OAM evaluation model and source-guard regressions."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from audit_stage136_oam_eight_limit import (
    ANCHORS,verify_source,sprite_scanline_model,OAMLimitError)


class SpriteSlotModel(unittest.TestCase):
    def test_nine_on_same_scanline_select_first_eight_with_overflow(self):
        y=[120]*9+[255]*55
        actual=sprite_scanline_model(y,124)
        self.assertEqual(actual['chosen_oam_indexes'],tuple(range(8)))
        self.assertTrue(actual['sprite_overflow_bit'])
        self.assertFalse(actual['native_nine_sprite_xbuf_proven'])

    def test_eight_visible_no_overflow(self):
        y=[120]*8+[255]*56
        got=sprite_scanline_model(y,124)
        self.assertEqual(got['selected_count'],8)
        self.assertFalse(got['sprite_overflow_bit'])

    def test_offscreen_and_oam_order(self):
        y=[255]*64
        for i in (1,2,6,11,13,20,40,50):
            y[i]=120
        r=sprite_scanline_model(y,124)
        self.assertEqual(r['chosen_oam_indexes'],(1,2,6,11,13,20,40,50))
        self.assertFalse(r['sprite_overflow_bit'])

    def test_sprite_8x16_lower_half_counts(self):
        y=[120]*9+[255]*55
        self.assertEqual(sprite_scanline_model(y,131)['selected_count'],0)
        b=sprite_scanline_model(y,131,height=16)
        self.assertEqual(b['selected_count'],8)
        self.assertTrue(b['sprite_overflow_bit'])

    def test_invalid_controls_rejected(self):
        good=[120]*64
        for key,val in (('height',9),('height',True),('scanline',256),
                        ('ppu_on',False),('oam_y',[120]*63),
                        ('oam_y',[120]*63+[True])):
            with self.subTest(key=key,val=val),self.assertRaises(OAMLimitError):
                kwargs={'oam_y':good,'scanline':124}
                kwargs[key]=val
                sprite_scanline_model(**kwargs)

    def test_source_order_mutations_fail_closed(self):
        source='\n'.join(ANCHORS)
        self.assertTrue(verify_source(source)['native_source_selection_order'])
        self.assertFalse(verify_source(source)['native_nine_sprite_xbuf_proven'])
        for anchor in ANCHORS:
            with self.subTest(anchor=anchor),self.assertRaises(OAMLimitError):
                verify_source(source.replace(anchor,'removed'))
        for invalid in (source+'\n'+source,12,'\n'.join(reversed(ANCHORS))):
            with self.assertRaises(OAMLimitError):
                verify_source(invalid)


if __name__=='__main__':
    unittest.main()
