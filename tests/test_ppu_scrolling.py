"""ROM-free synthetic 2x2 PPU-scroll and sprite priority regression."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from ppu_scroll import resolve_pixel,scroll_background_pixel,opaque_background_pixel
from compare_rendered_frame import reconstructed_indices,compare_pixels


def fixture():
    ppu=bytearray(0x4000)
    ram=bytearray(0x800)
    for n in range(64):ram[0x700+4*n]=240
    ppu[0x3f00]=0x0f
    for slot,color in ((1,0x11),(2,0x21),(3,0x31),(13,0x16)):
        ppu[0x3f00+slot]=color
    ppu[16]=0x80
    ppu[2*16+8]=0x80
    ppu[3*16]=ppu[3*16+8]=0x80
    ppu[4*16]=0x80
    for n in range(4):ppu[0x2000+n*1024]=n+1
    ppu[0x23c0+3*0x400]=0x03  # table 3 first quadrant: palette 3
    return ppu,ram


class ScrollTests(unittest.TestCase):
    def test_four_tables_and_pixel_seams(self):
        ppu,_=fixture()
        self.assertEqual(scroll_background_pixel(ppu,0,0,0,0),0x11)
        self.assertEqual(scroll_background_pixel(ppu,0,1,0,0,255,0),0x21)
        self.assertEqual(scroll_background_pixel(ppu,0,0,1,0,0,239),0x31)
        self.assertEqual(scroll_background_pixel(ppu,0,1,1,0,255,239),0x16)
        self.assertEqual(resolve_pixel(0,1,1,255,239),(3,0,0))

    def test_wrap_and_nametable_selection(self):
        self.assertEqual(resolve_pixel(1,1,0,255,0),(0,0,0))
        self.assertEqual(resolve_pixel(2,0,1,0,239),(0,0,0))
        self.assertEqual(resolve_pixel(3,1,1,255,239),(0,0,0))
        self.assertEqual(resolve_pixel(2,255,239,255,239),(1,254,238))

    def test_fine_scroll_across_non_aligned_pixels(self):
        ppu,_=fixture()
        self.assertEqual(scroll_background_pixel(ppu,0,0,0,0,1,0),0x0f)
        self.assertEqual(scroll_background_pixel(ppu,0,0,0,0,0,1),0x0f)
        self.assertEqual(scroll_background_pixel(ppu,0,255,0,0,1,0),0x21)

    def test_sprite_behind_background_uses_scrolled_opaque_tile(self):
        ppu,ram=fixture()
        ppu[0x2000+32+31]=1 # tile row 1, last tile
        ppu[16+2]=0x01      # last pixel of row 2 is opaque
        ppu[0x2000+0x400]=0 # horizontal neighbor transparent
        ppu[5*16]=0x80       # independently drawn sprite test tile
        ppu[0x3f11]=0x22
        ram[0x700:0x704]=bytes([9,5,0x20,0])  # behind background
        shifted=reconstructed_indices(ppu,ram,0,0,True,8,0,0x1e,scroll_x=255)
        normal=reconstructed_indices(ppu,ram,0,0,True,8,0,0x1e)
        self.assertEqual(shifted[10*256],0x11)
        self.assertEqual(normal[10*256],0x22)
        self.assertEqual(opaque_background_pixel(ppu,0,0,10,0,255,0),1)
        self.assertEqual(opaque_background_pixel(ppu,0,1,10,0,255,0),0)

    def test_reference_comparison_detects_wrong_scroll(self):
        ppu,ram=fixture()
        observed=reconstructed_indices(ppu,ram,0,0,scroll_x=255,scroll_y=239)
        bad=reconstructed_indices(ppu,ram,0,0)
        good_result,_=compare_pixels(observed,observed)
        bad_result,_=compare_pixels(bad,observed)
        self.assertEqual(good_result['different_pixels'],0)
        self.assertGreater(bad_result['different_pixels'],0)

    def test_invalid_unmodeled_scroll_modes(self):
        ppu,ram=fixture()
        for x,y in ((-1,0),(256,0),(0,240)):
            with self.assertRaises(ValueError):resolve_pixel(0,x,y)
        for x,y in ((256,0),(0,240),(-1,0)):
            with self.assertRaisesRegex(ValueError,'Scroll'):
                resolve_pixel(0,0,0,x,y)
        with self.assertRaises(ValueError):resolve_pixel(4,0,0)
        with self.assertRaises(ValueError):reconstructed_indices(ppu,ram,0,0,scroll_y=240)


if __name__=='__main__':
    unittest.main()
