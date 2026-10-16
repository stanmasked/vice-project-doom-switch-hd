"""Synthetic/ROM-free reference capture tests. No commercial assets included."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from render_ppu_snapshot import (NES_RGB,load_snapshot,palette_color,bg_pixel,
                                 render_background,pattern_bases,inspect)

def invented_ppu():
    p=bytearray(16384)
    # Invented tile 1: first row plane 0 all one, other rows transparent.
    p[16]=255
    p[0x3f00]=0x0f
    p[0x3f01]=0x11
    p[0x3f05]=0x21
    p[0x3f09]=0x31
    p[0x3f0d]=0x16
    p[0x2000]=p[0x2002]=p[0x2000+2*32]=p[0x2000+2*32+2]=1
    p[0x23c0]=0xe4
    return p

class PpuSnapshotTests(unittest.TestCase):
    def test_four_attribute_quadrants(self):
        p=invented_ppu()
        self.assertEqual(bg_pixel(p,0,0,0,0),0x11)
        self.assertEqual(bg_pixel(p,0,16,0,0),0x21)
        self.assertEqual(bg_pixel(p,0,0,16,0),0x31)
        self.assertEqual(bg_pixel(p,0,16,16,0),0x16)

    def test_transparent_uses_universal_color_and_mirror(self):
        p=invented_ppu()
        self.assertEqual(bg_pixel(p,0,1,1,0),0x0f)
        p[0x3f10]=0x2e
        self.assertEqual(palette_color(p,0x10),0x0f)
        self.assertEqual(palette_color(p,0),0x0f)

    def test_two_pattern_tables(self):
        p=invented_ppu()
        p[16]=0
        p[0x1010]=255
        self.assertEqual(bg_pixel(p,0,0,0,0),0x0f)
        self.assertEqual(bg_pixel(p,0,0,0,0x1000),0x11)
        im=render_background(p,0,0x1000,2)
        self.assertEqual(im.size,(512,480))
        self.assertEqual(im.getpixel((0,0)),NES_RGB[0x11])

    def test_known_and_unknown_ppuctrl(self):
        self.assertEqual(pattern_bases({'ppuctrl':'10'})[0],[0x1000])
        self.assertEqual(pattern_bases({'ppuctrl':'00'})[0],[0])
        self.assertEqual(pattern_bases({'ppuctrl':'unknown'})[0],[0,0x1000])
        self.assertEqual(pattern_bases({})[0],[0,0x1000])
        self.assertEqual(pattern_bases({},'0x0000')[0],[0])

    def test_capture_reading_and_diagnostics(self):
        with tempfile.TemporaryDirectory() as temp:
            stem=Path(temp)/'frame_000120'
            Path(str(stem)+'.ppu.bin').write_bytes(invented_ppu())
            Path(str(stem)+'.ram.bin').write_bytes(bytes(range(256))*8)
            Path(str(stem)+'.meta.txt').write_text('frame=120\nppuctrl=10\n',encoding='utf-8')
            p,ram,meta=load_snapshot(stem)
            self.assertEqual(meta['frame'],'120')
            self.assertEqual(inspect(p,ram,meta,[0x1000])['chr_zero_page_3d_42'],list(range(0x3d,0x43)))
            self.assertEqual(inspect(p,ram,meta,[0x1000])['nametables'][0]['unique_tile_ids'],2)
            Path(str(stem)+'.ram.bin').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'2048'):load_snapshot(stem)
            Path(str(stem)+'.ram.bin').unlink()
            self.assertIsNone(load_snapshot(stem)[1])
            Path(str(stem)+'.ppu.bin').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'16384'):load_snapshot(stem)

    def test_metadata_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            stem=Path(temp)/'frame_000120'
            Path(str(stem)+'.ppu.bin').write_bytes(invented_ppu())
            meta=Path(str(stem)+'.meta.txt')
            meta.write_text('frame=120\nframe=121\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Duplicate'):load_snapshot(stem)
            meta.write_text('not-an-assignment',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Malformed'):load_snapshot(stem)

    def test_input_validation(self):
        p=invented_ppu()
        with self.assertRaisesRegex(ValueError,'Nametable'):bg_pixel(p,4,0,0,0)
        with self.assertRaisesRegex(ValueError,'Pattern base'):bg_pixel(p,0,0,0,0x800)
        with self.assertRaisesRegex(ValueError,'Scale'):render_background(p,0,0,9)
        with self.assertRaisesRegex(ValueError,'Palette entry'):palette_color(p,32)
        with self.assertRaisesRegex(ValueError,'16KiB'):bg_pixel(bytes(8),0,0,0,0)

if __name__=='__main__':unittest.main()
