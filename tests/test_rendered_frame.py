"""Synthetic FCEUX screen-reference tests; no proprietary game contents."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from compare_rendered_frame import (PIXELS,compare_pixels,evaluate,
                                    load_reference,reconstructed_indices)

def fake_mem():
    ppu=bytearray(16384)
    ppu[0x3f00]=0x0f
    ppu[0x3f01]=0x21
    ppu[0x3f11]=0x30
    ppu[0x2000]=1
    ppu[16]=0x80
    ram=bytearray(2048)
    for i in range(64):ram[0x700+4*i]=240
    return ppu,ram

class ReferenceFrameTests(unittest.TestCase):
    def test_identical_background_reference(self):
        ppu,ram=fake_mem()
        predicted=reconstructed_indices(ppu,ram,0,0)
        self.assertEqual(predicted[0],0x21)
        self.assertEqual(predicted[1],0x0f)
        result,heat=compare_pixels(predicted,predicted)
        self.assertEqual(result['different_pixels'],0)
        self.assertEqual(result['compared_pixels'],PIXELS)
        self.assertEqual(heat.size,(256,240))

    def test_unknown_palette_and_actual_differences(self):
        pred=bytearray([3]*PIXELS)
        actual=bytearray(pred)
        actual[0]=4
        actual[1]=254
        actual[256*10+9]=5
        result,heat=compare_pixels(pred,actual)
        self.assertEqual(result['different_pixels'],2)
        self.assertEqual(result['unknown_palette_pixels'],1)
        self.assertEqual(result['compared_pixels'],PIXELS-1)
        self.assertEqual(result['highest_mismatch_scanlines'][0]['row'],0)
        self.assertEqual(heat.getpixel((0,0)),(239,73,58))
        self.assertEqual(heat.getpixel((1,0)),(60,99,150))

    def test_sprite_overlay_and_clip_masks(self):
        ppu,ram=fake_mem()
        ram[0x700:0x704]=bytes([0,1,0,0])
        spr=reconstructed_indices(ppu,ram,0,0,True,8,0,0x1e)
        self.assertEqual(spr[256],0x30)
        clipped=reconstructed_indices(ppu,ram,0,0,True,8,0,0x18)
        self.assertEqual(clipped[256],0x0f)
        bg=reconstructed_indices(ppu,ram,0,0,False,8,0,0x1e)
        self.assertEqual(bg[256],0x0f)

    def test_reference_file_size_and_index_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            prefix=Path(temp)/'frame_000120'
            Path(str(prefix)+'.screen.rgb.bin').write_bytes(bytes(PIXELS*3))
            pal=Path(str(prefix)+'.screen.pal.bin')
            pal.write_bytes(bytes(PIXELS))
            rgb,indices=load_reference(prefix)
            self.assertEqual(len(rgb),PIXELS*3)
            self.assertEqual(len(indices),PIXELS)
            pal.write_bytes(bytes([64])+bytes(PIXELS-1))
            with self.assertRaisesRegex(ValueError,'illegal NES'):
                load_reference(prefix)
            pal.write_bytes(bytes(9))
            with self.assertRaisesRegex(ValueError,'61440'):
                load_reference(prefix)

    def test_evaluate_known_and_unknown_ppuctrl(self):
        ppu,ram=fake_mem()
        with tempfile.TemporaryDirectory() as temp:
            prefix=Path(temp)/'frame_000120'
            Path(str(prefix)+'.ppu.bin').write_bytes(ppu)
            Path(str(prefix)+'.ram.bin').write_bytes(ram)
            Path(str(prefix)+'.screen.rgb.bin').write_bytes(bytes(PIXELS*3))
            Path(str(prefix)+'.screen.pal.bin').write_bytes(reconstructed_indices(ppu,ram,0,0,False,8,0,0x1e))
            meta=Path(str(prefix)+'.meta.txt')
            meta.write_text('frame=120\nppuctrl=00\nppumask=1E\n',encoding='utf8')
            result,_=evaluate(prefix)
            self.assertEqual(result['different_pixels'],0)
            self.assertTrue(result['ppuctrl_observed'])
            meta.write_text('frame=120\nppuctrl=unknown\nppumask=unknown\n',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'PPUCTRL unknown'):
                evaluate(prefix)
            with self.assertRaisesRegex(ValueError,'Cannot determine sprite'):
                evaluate(prefix,base=0,mode='sprites')

    def test_invalid_dimensions_and_settings(self):
        ppu,ram=fake_mem()
        with self.assertRaises(ValueError):reconstructed_indices(ppu,ram,0,0x2000)
        with self.assertRaises(ValueError):reconstructed_indices(ppu,None,0,0,True)
        with self.assertRaises(ValueError):compare_pixels(bytes(12),bytes(PIXELS))
        with self.assertRaises(ValueError):reconstructed_indices(ppu,ram,0,0,True,12)

if __name__=='__main__':unittest.main()
