"""ROM-free synthetic OAM tests. No real game assets or ROM segments."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from render_oam_sprites import sprite_pixel,overlay_sprites,observed_ppuctrl
from render_ppu_snapshot import NES_RGB

def fixture():
    p=bytearray(16384)
    ram=bytearray(2048)
    for i in range(64):ram[0x700+i*4]=240
    p[0x3f00]=0x0f
    p[0x3f01]=0x11
    p[0x3f11]=0x21
    p[0x3f15]=0x31
    for y in range(8):p[16+y]=128>>y
    return p,ram

class SpriteTests(unittest.TestCase):
    def test_oam_y_plus_one_and_transparency(self):
        p,ram=fixture()
        ram[0x700:0x704]=bytes([9,1,0,16])
        image=overlay_sprites(p,ram,ppumask=0x1e)
        self.assertEqual(image.getpixel((16,10)),NES_RGB[0x21])
        self.assertEqual(image.getpixel((17,10)),NES_RGB[0x0f])
        self.assertEqual(image.getpixel((16,9)),NES_RGB[0x0f])

    def test_horizontal_and_vertical_flip(self):
        p,ram=fixture()
        for y in range(1,8):p[16+y]=0
        ram[0x700:0x704]=bytes([9,1,0xc0,16])
        image=overlay_sprites(p,ram,ppumask=0x1e)
        self.assertEqual(image.getpixel((16,10)),NES_RGB[0x0f])
        self.assertEqual(image.getpixel((23,17)),NES_RGB[0x21])

    def test_behind_nonzero_background_and_palette(self):
        p,ram=fixture()
        p[0x2000+32*2+2]=2
        p[2*16]=0x80
        ram[0x700:0x704]=bytes([15,1,0x21,16])
        image=overlay_sprites(p,ram,ppumask=0x1e)
        self.assertEqual(image.getpixel((16,16)),NES_RGB[0x11])
        self.assertEqual(image.getpixel((17,17)),NES_RGB[0x31])

    def test_low_index_sprite_priority(self):
        p,ram=fixture()
        ram[0x700:0x704]=bytes([9,1,0,16])
        ram[0x704:0x708]=bytes([9,1,1,16])
        image=overlay_sprites(p,ram,ppumask=0x1e)
        self.assertEqual(image.getpixel((16,10)),NES_RGB[0x21])

    def test_8_by_16_odd_tile_selects_second_pattern_table(self):
        p,ram=fixture()
        p[0x1000+2*16]=0x80
        p[0x1000+3*16]=0x40
        self.assertEqual(sprite_pixel(p,3,0,0,16,0),1)
        self.assertEqual(sprite_pixel(p,3,1,8,16,0),1)
        self.assertEqual(sprite_pixel(p,3,0,0,8,0),0)

    def test_sprite_mask_clips_leftmost_pixels(self):
        p,ram=fixture()
        ram[0x700:0x704]=bytes([9,1,0,0])
        self.assertEqual(overlay_sprites(p,ram,ppumask=0x18).getpixel((0,10)),NES_RGB[0x0f])
        self.assertEqual(overlay_sprites(p,ram,ppumask=0x1c).getpixel((0,10)),NES_RGB[0x21])
        self.assertEqual(overlay_sprites(p,ram,ppumask=0).getpixel((0,10)),NES_RGB[0x0f])

    def test_metadata_and_input_validation(self):
        self.assertEqual(observed_ppuctrl({'ppuctrl':'28'}),0x28)
        self.assertIsNone(observed_ppuctrl({}))
        with self.assertRaises(ValueError):observed_ppuctrl({'ppuctrl':'1FF'})
        p,ram=fixture()
        with self.assertRaisesRegex(ValueError,'16KiB'):overlay_sprites(bytes(1),ram)
        with self.assertRaisesRegex(ValueError,'Invalid sprite'):overlay_sprites(p,ram,sprite_height=12)

if __name__=='__main__':unittest.main()
