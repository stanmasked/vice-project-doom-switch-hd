"""Stage132 pinned source guards, asymmetric sprite flip model, 8x16 mapping."""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from audit_stage132_sprite_flips import (
    SpriteFlipError, verify_source, flipped_pattern, FETCH_ANCHORS, RASTER_ANCHORS,
)


class FlipSource(unittest.TestCase):
    def test_exact_pinned_source_contract_separate_fetch_and_raster(self):
        source = ('\n'.join(RASTER_ANCHORS) + '\n' +
                  '\n'.join(FETCH_ANCHORS))
        data = verify_source(source)
        self.assertTrue(data['horizontal_reverse_source'])
        self.assertTrue(data['vertical_flip_source'])
        self.assertFalse(data['native_flip_pixels_proven'])

    def test_missing_duplicate_reordered_and_wrong_type_fail(self):
        source = '\n'.join(RASTER_ANCHORS + FETCH_ANCHORS)
        for anchor in RASTER_ANCHORS + FETCH_ANCHORS:
            with self.subTest(anchor=anchor), self.assertRaises(SpriteFlipError):
                verify_source(source.replace(anchor, 'removed', 1))
        for wrong in (source + '\n' + source, 17,
                      '\n'.join(reversed(RASTER_ANCHORS)) + '\n' +
                      '\n'.join(FETCH_ANCHORS)):
            with self.assertRaises(SpriteFlipError):
                verify_source(wrong)


class PixelPatterns(unittest.TestCase):
    def setUp(self):
        self.low = bytes((0x80, 0, 0, 0, 0, 0, 0, 0x01))
        self.high = bytes(8)

    def test_four_flips_asymmetric_row0_and_row7(self):
        # Unflipped: top-left / bottom-right. Horizontal flip swaps left/right;
        # vertical flip swaps the two rows; both return to top-left.
        expected = {
            (False, False): ((0, 0), (7, 7)),
            (True, False): ((7, 0), (0, 7)),
            (False, True): ((7, 0), (0, 7)),
            (True, True): ((0, 0), (7, 7)),
        }
        for (h,v), points in expected.items():
            with self.subTest(h=h, v=v):
                nonzero = []
                for y in range(8):
                    for x in range(8):
                        pixel, address = flipped_pattern(
                            tile=2, x=x, y=y, low=self.low, high=self.high,
                            hflip=h, vflip=v)
                        if pixel: nonzero.append((x,y))
                        self.assertEqual(address, 0x1000 + 2*16 +
                                         (7-y if v else y))
                self.assertEqual(tuple(nonzero),
                                 tuple(sorted(points, key=lambda z:(z[1],z[0]))))

    def test_high_plane_and_nontransparent_pattern_three(self):
        for x in range(8):
            for y in range(8):
                p, _ = flipped_pattern(tile=2, x=x, y=y,
                                       low=bytes((255,)*8),
                                       high=bytes((255,)*8))
                self.assertEqual(p,3)

    def test_8x16_vertical_flip_swaps_tile_half_and_bank(self):
        low = bytes((0x80,)+ (0,)*6 + (0x01,) + (0,)*7 +(0x04,))
        high = bytes(16)
        for tile in (2, 3):
            for v in (False,True):
                bank = 0x1000 if tile&1 else 0
                for y in range(16):
                    row = 15-y if v else y
                    p,addr=flipped_pattern(tile=tile,x=0,y=y,low=low,high=high,
                                           height=16,vflip=v)
                    expected_addr=bank+((tile&~1)+(row>>3))*16+(row&7)
                    self.assertEqual(addr, expected_addr)
                    self.assertEqual(p,(low[row]>>7)&1)

    def test_reject_invalid_or_wrongly_sized_controls(self):
        arguments=dict(tile=2,x=0,y=0,low=self.low,high=self.high)
        for field,value in (('tile',True),('tile',-1),('x',8),('y',8),
                            ('low',b'\0'),('high',[]),('hflip',1),
                            ('height',15),('height','8'),('sprite_table_high',0)):
            with self.subTest(field=field,value=value):
                kwargs=dict(arguments)
                kwargs[field]=value
                with self.assertRaises(SpriteFlipError):
                    flipped_pattern(**kwargs)


if __name__=='__main__':
    unittest.main()
