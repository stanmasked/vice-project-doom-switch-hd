"""Purely fictional ROM fixture; no copyrighted source game data."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from build_fceux_smoke_rom import build_rom,HEADER,PRG_SIZE,CHR_SIZE

class InventedRomTests(unittest.TestCase):
    def test_size_and_vectors(self):
        rom=build_rom()
        self.assertEqual(rom[:16],HEADER)
        self.assertEqual(len(rom),16+PRG_SIZE+CHR_SIZE)
        self.assertEqual(rom[16:19],b"\x78\xd8\xa2")
        self.assertEqual(rom[16+PRG_SIZE-6:16+PRG_SIZE],b"\x00\x80"*3)
        self.assertEqual(rom[-CHR_SIZE:],bytes(CHR_SIZE))

    def test_safe_infinite_cpu_loop(self):
        rom=build_rom()
        self.assertEqual(rom[16+28:16+31],b"\x4c\x1c\x80")

    def test_byte_identical_rebuild(self):
        self.assertEqual(build_rom(),build_rom())
if __name__=="__main__":unittest.main()
