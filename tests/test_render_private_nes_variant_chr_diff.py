"""Synthetic original-made pixel patterns only; no commercial ROM/art."""
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from render_private_nes_variant_chr_diff import decode_chr_bank, render_difference_atlas
from test_audit_private_nes_variant_banks import fake_rom

class PrivateCHRAtlasTests(unittest.TestCase):
    def test_exact_bitplane_reconstruction(self):
        bank=bytearray(1024)
        bank[0]=0x80
        bank[8]=0x40
        bitmap=decode_chr_bank(bytes(bank))
        self.assertEqual(bitmap.size,(64,64))
        self.assertEqual(bitmap.getpixel((0,0)),94)
        self.assertEqual(bitmap.getpixel((1,0)),165)
        self.assertEqual(bitmap.getpixel((2,0)),20)

    def test_reject_short_bank(self):
        with self.assertRaisesRegex(ValueError,"1KB"):
            decode_chr_bank(bytes(1023))

    def test_synthetic_one_bank_renders_correctly(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            us=root/"us.nes";jp=root/"jp.nes";out=root/"difference.png"
            first=fake_rom(nes2=True)
            changed=bytearray(fake_rom())
            changed[16+131072+124*1024]=255
            us.write_bytes(first);jp.write_bytes(changed)
            report=render_difference_atlas(us,jp,out)
            self.assertEqual(report["different_chr_banks"],[124])
            with Image.open(out) as png:
                self.assertEqual(png.format,"PNG")
                self.assertEqual(png.mode,"RGB")
                self.assertTrue(png.width>=256 and png.height>=512)
            self.assertFalse(report["actual_palette_or_stage_proven"])

    def test_identical_chr_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            a=root/"a.nes";b=root/"b.nes";out=root/"diff.png"
            a.write_bytes(fake_rom());b.write_bytes(fake_rom(nes2=True))
            with self.assertRaisesRegex(ValueError,"identical"):
                render_difference_atlas(a,b,out)
            self.assertFalse(out.exists())

    def test_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            target=root/"existing.png"
            target.write_bytes(b"other")
            with self.assertRaisesRegex(ValueError,"overwrite"):
                render_difference_atlas(root/"absent.nes",root/"other.nes",target)
            self.assertEqual(target.read_bytes(),b"other")

    def test_git_checkout_output_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/".git").mkdir()
            with self.assertRaisesRegex(ValueError,"inside Git"):
                render_difference_atlas(root/"a.nes",root/"b.nes",root/"atlas.png")

    def test_scale_outside_bounds_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaisesRegex(ValueError,"scale"):
                render_difference_atlas(root/"a.nes",root/"b.nes",root/"atlas.png",scale=0)

    def test_limit_of_16_changed_banks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            a=root/"a.nes";b=root/"b.nes"
            a.write_bytes(fake_rom())
            r=bytearray(fake_rom())
            for i in range(17):
                r[16+131072+1024*i]=255
            b.write_bytes(r)
            with self.assertRaisesRegex(ValueError,"too many"):
                render_difference_atlas(a,b,root/"atlas.png")

if __name__=="__main__":
    unittest.main()
