"""Synthetic-only corruption and fail-closed guest-audit invariants."""
import struct
import sys
import unittest
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from generate_corrupt_synthetic_road_bundle import corrupt
from generate_synthetic_road_bundle import synthetic_bundle
class CorruptRoadFixtureTests(unittest.TestCase):
    def test_crc_mismatch(self):
        valid=synthetic_bundle()
        broken=corrupt("bad_crc")
        self.assertEqual(len(broken),164)
        self.assertNotEqual(zlib.crc32(broken[16:]),
                            struct.unpack_from("<I",broken,12)[0])
        self.assertNotEqual(valid,broken)
    def test_valid_crc_but_invalid_first_anchor(self):
        valid=synthetic_bundle()
        broken=corrupt("bad_anchor")
        self.assertEqual(len(broken),164)
        self.assertEqual(zlib.crc32(broken[16:]),
                         struct.unpack_from("<I",broken,12)[0])
        self.assertEqual(broken[18],67)
        self.assertEqual(valid[18],66)
    def test_truncation(self):
        self.assertEqual(len(corrupt("truncated")),163)
    def test_bad_variant(self):
        with self.assertRaises(ValueError):corrupt("private_original")
    def test_no_original_images_in_any_fixture(self):
        for mode in ("bad_crc","bad_anchor","truncated"):
            raw=corrupt(mode)
            self.assertTrue(raw.startswith(b"VPDROAD1"))
            self.assertNotIn(b".nes",raw)
            self.assertNotIn(b".fm2",raw)
if __name__=="__main__":unittest.main()
