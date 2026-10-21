"""ROM-free, hand-authored NES2.0 MMC3 cartridge layout regressions."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from build_fceux_smoke_mmc3_nes2 import build_rom,HEADER,PRG_SIZE,CHR_SIZE
from build_fceux_smoke_rom import build_rom as build_nrom


class SyntheticNes2Mapper4Tests(unittest.TestCase):
    def test_mapper4_fixed_128k_prg_chr(self):
        rom=build_rom()
        self.assertEqual(rom[:16],HEADER)
        self.assertEqual((rom[6]>>4)|(rom[7]&0xf0),4)
        self.assertEqual(rom[7]&12,8)
        self.assertEqual((rom[4],rom[5]),(8,16))
        self.assertEqual(len(rom),16+PRG_SIZE+CHR_SIZE)
        self.assertEqual(rom[-CHR_SIZE:],bytes(CHR_SIZE))

    def test_6502_reset_vectors_target_fixed_bank(self):
        prg=build_rom()[16:16+PRG_SIZE]
        self.assertEqual(prg[-6:],b"\x00\xe0"*3)
        self.assertEqual(prg[-8192:-8192+46],build_nrom()[16:16+46])
        self.assertEqual(prg[-8192+46:-8192+49],b"\x4c\x1c\xe0")

    def test_deterministic_original_mmc3(self):
        self.assertEqual(build_rom(),build_rom())
        self.assertNotEqual(build_rom(),build_nrom())


if __name__=="__main__":
    unittest.main()
