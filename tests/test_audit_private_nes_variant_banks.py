"""Invented NES cartridge banks only; no commercial or user ROMs in CI."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_nes_variant_banks import compare_roms,read_layout,BANK_BYTES


def fake_rom(*,nes2=False,mapper=4,tag=0):
    h=bytearray(16)
    h[:4]=b"NES\x1a"
    h[4]=8
    h[5]=16
    h[6]=(mapper&0xf)<<4
    h[7]=mapper&0xf0
    if nes2:h[7]|=0x08
    prg=bytes([tag]*131072)
    chr_=bytes([3]*131072)
    return bytes(h)+prg+chr_


class RomVariantTests(unittest.TestCase):
    def test_same_payload_different_header_reports_full_match(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"first.nes";b=Path(d)/"second.nes"
            a.write_bytes(fake_rom(nes2=True))
            b.write_bytes(fake_rom(nes2=False))
            r=compare_roms(a,b)
            self.assertEqual(r["mapper"],4)
            self.assertEqual(r["chr_comparison"]["identical_1kb_banks"],128)
            self.assertEqual(r["prg_comparison"]["identical_1kb_banks"],128)
            self.assertTrue(r["first_rom_uses_nes2"])
            self.assertFalse(r["second_rom_uses_nes2"])
            self.assertFalse(r["shared_level_geometry_proven"])

    def test_three_changed_chr_banks_account_exact_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"first.nes";b=Path(d)/"second.nes"
            original=fake_rom()
            modified=bytearray(original)
            for bank,length in ((124,27),(125,51),(126,67)):
                start=16+131072+bank*BANK_BYTES
                modified[start:start+length]=bytes([8])*length
            a.write_bytes(original);b.write_bytes(modified)
            r=compare_roms(a,b)
            self.assertEqual(r["chr_comparison"]["identical_1kb_banks"],125)
            self.assertEqual([x["index"] for x in r["chr_comparison"]["different_banks"]],[124,125,126])
            self.assertEqual(r["chr_comparison"]["different_byte_count"],145)

    def test_no_identical_chr_cannot_claim_shared_patterns(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            a=root/"a.nes";b=root/"b.nes"
            a.write_bytes(fake_rom())
            changed=bytearray(fake_rom())
            changed[-131072:]=bytes([4])*131072
            b.write_bytes(changed)
            report=compare_roms(a,b)
            self.assertEqual(report["chr_comparison"]["identical_1kb_banks"],0)
            self.assertFalse(report["shared_chr_proven_at_equal_offsets"])
            self.assertFalse(report["shared_level_geometry_proven"])

    def test_prg_difference_does_not_erase_identical_chr(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"first.nes";b=Path(d)/"second.nes"
            altered=bytearray(fake_rom())
            altered[16+4096]=99
            a.write_bytes(fake_rom());b.write_bytes(altered)
            r=compare_roms(a,b)
            self.assertEqual(r["prg_comparison"]["different_1kb_banks"],1)
            self.assertEqual(r["prg_comparison"]["different_banks"][0]["index"],4)
            self.assertEqual(r["chr_comparison"]["different_1kb_banks"],0)

    def test_reject_different_mapper(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a.nes";b=Path(d)/"b.nes"
            a.write_bytes(fake_rom(mapper=4))
            b.write_bytes(fake_rom(mapper=2))
            with self.assertRaisesRegex(ValueError,"mapper"):
                compare_roms(a,b)

    def test_reject_unexpected_trailing_data(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a.nes"
            a.write_bytes(fake_rom()+b"X")
            with self.assertRaisesRegex(ValueError,"canonical"):
                read_layout(a)

    def test_reject_trainer(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a.nes"
            bad=bytearray(fake_rom())
            bad[6]|=0x04
            a.write_bytes(bad)
            with self.assertRaisesRegex(ValueError,"trainer"):
                read_layout(a)

    def test_reject_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            base=root/"base.nes";link=root/"linked.nes"
            base.write_bytes(fake_rom())
            try:link.symlink_to(base)
            except OSError as exc:self.skipTest(str(exc))
            with self.assertRaisesRegex(ValueError,"symlinked"):
                read_layout(link)

    def test_reject_mismatched_lengths(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            a=root/"a.nes";b=root/"b.nes"
            a.write_bytes(fake_rom())
            shortened=bytearray(fake_rom())
            shortened[5]=15
            shortened=shortened[:-8192]
            b.write_bytes(shortened)
            with self.assertRaisesRegex(ValueError,"layout"):
                compare_roms(a,b)

    def test_invalid_ines_marker(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"bad.nes"
            root.write_bytes(b"BAD!"+fake_rom()[4:])
            with self.assertRaisesRegex(ValueError,"NES cartridge"):
                read_layout(root)

if __name__=="__main__":
    unittest.main()
