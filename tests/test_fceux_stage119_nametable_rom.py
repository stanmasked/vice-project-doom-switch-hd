"""Fail-closed source checks for generated Stage119 graphics evidence."""
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from make_stage119_nametable_rom import make_rom, nametable_init, START_RENDER_SETUP
from make_stage110_synthetic_midframe_rom import program
from inject_fceux_stage119_nametable_pixels import patch, PIXEL, WRITE

class Generated(unittest.TestCase):
    def test_nt_loop_and_ppu_latch_restore(self):
        loop = bytes((0xa2,0,0x8a,0x29,1,0x8d,7,0x20,0xe8,0xd0,0xf7))
        init = nametable_init()
        self.assertEqual(init.count(loop),16)
        self.assertEqual(len(loop)-9,2)
        self.assertTrue(init.endswith(bytes((0xa9,0,0x8d,5,0x20,0x8d,5,0x20))))

    def test_differentiated_and_control_have_identical_prg(self):
        with tempfile.TemporaryDirectory() as tmp:
            for fine in (1,3,5,7):
                a,b=Path(tmp)/"a.nes",Path(tmp)/"b.nes"
                make_rom(a,first=fine)
                make_rom(b,first=fine,differentiated=False)
                original,control=a.read_bytes(),b.read_bytes()
                self.assertEqual(len(original),49168)
                self.assertEqual(original[:32784],control[:32784])
                self.assertNotEqual(original[32784:],control[32784:])
                self.assertEqual(original[:16],b"NES\x1a\x02\x02\x40"+bytes(9))
                self.assertEqual(original[32784+1024:32784+1040],bytes(16))
                self.assertEqual(original[32784+1040:32784+1056],bytes((255,))*16)

    def test_legacy_program_is_untouched(self):
        old=program(dynamic_fine_scroll=3,second_dynamic_scroll=13)
        self.assertEqual(old.count(START_RENDER_SETUP),1)
        self.assertNotIn(nametable_init(),old)

    def test_invalid_values_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            for fine in (-1,0,2,8,3.5,"3",True):
                with self.subTest(fine=fine),self.assertRaises(ValueError):
                    make_rom(Path(tmp)/"bad.nes",first=fine)
            for key in ("switch","differentiated"):
                with self.assertRaises(ValueError):
                    make_rom(Path(tmp)/"bad.nes",**{key:1})

class PinnedHooks(unittest.TestCase):
    SAMPLE=(b"vpd_ppu_probe::stage115_edge_read(sl, xt, 0, 0);\r\n"+
            WRITE+b"\r\n"+PIXEL+b"\r\n")
    def test_exact_native_nt_pixel_observer(self):
        out=patch(self.SAMPLE)
        self.assertEqual(out.count(b"stage119_write("),1)
        self.assertEqual(out.count(b"stage119_pixel("),1)
        self.assertIn(b"bgdata.main[bgtile].nt",out)

    def test_bad_source_rejected(self):
        for data in (self.SAMPLE+self.SAMPLE,patch(self.SAMPLE),
                     self.SAMPLE.replace(WRITE,b"missing"),
                     self.SAMPLE.replace(PIXEL,b"missing"),
                     self.SAMPLE.replace(b"stage115_edge_read",b"missing")):
            with self.assertRaises(ValueError):
                patch(data)

    def test_line_endings_and_type(self):
        lf=patch(self.SAMPLE.replace(b"\r\n",b"\n"))
        self.assertNotIn(b"\r\n",lf)
        with self.assertRaises(TypeError):
            patch(self.SAMPLE.decode("ascii"))

if __name__=="__main__":
    unittest.main()
