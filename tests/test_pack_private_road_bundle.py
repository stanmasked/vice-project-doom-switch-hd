"""All source frames are synthesized in memory. No original media."""
from __future__ import annotations
import copy
import struct
import sys
import unittest
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_audit_private_legacy_road_geometry import synthetic
from pack_private_road_bundle import (pack_numeric_report, output_private_only,
                                      EXPECTED_BYTES,REJECTED,MAGIC)

class PrivateRoadBundleTests(unittest.TestCase):
    def test_full_synthetic_window_pack(self):
        raw=pack_numeric_report(synthetic())
        self.assertEqual(len(raw),EXPECTED_BYTES)
        magic,version,count,crc=struct.unpack_from("<8sHHI",raw)
        self.assertEqual((magic,version,count),(MAGIC,1,37))
        self.assertEqual(zlib.crc32(raw[16:]),crc)
        records=list(struct.iter_unpack("<HBB",raw[16:]))
        self.assertEqual(len(records),37)
        self.assertEqual([r[0] for r in records],
                         [f for f in range(600,921,8) if f not in REJECTED])
        self.assertEqual(records[0],(600,66,188))
        self.assertEqual(records[-1],(920,116,203))
        self.assertNotIn(b"FCEUX",raw)
        self.assertNotIn(b"NES",raw)
    def test_damaged_original_observation_rejected(self):
        r=synthetic()
        r["frames"][20]["observed_left_edge"]=99
        with self.assertRaises(ValueError):pack_numeric_report(r)
    def test_missing_movie_frame_rejected(self):
        r=synthetic()
        r["frames"].pop()
        with self.assertRaises(ValueError):pack_numeric_report(r)
    def test_rejected_slot_cannot_be_reconstructed(self):
        r=synthetic()
        r["frames"][14].update(observed_left_edge=10)
        with self.assertRaises(ValueError):pack_numeric_report(r)
    def test_wrong_frame_order_rejected(self):
        r=synthetic()
        r["frames"][1],r["frames"][2]=r["frames"][2],r["frames"][1]
        with self.assertRaises(ValueError):pack_numeric_report(r)
    def test_original_media_filename_metadata_rejected(self):
        r=synthetic()
        r["original_rom"]="private.nes"
        with self.assertRaises(ValueError):pack_numeric_report(r)
    def test_corrupted_report_extrema_rejected(self):
        r=synthetic()
        r["summary"]["minimum_observed_width"]=1
        with self.assertRaises(ValueError):pack_numeric_report(r)
    def test_forged_rom_fm2_hash_not_accepted_as_provenance(self):
        r=synthetic()
        r["rom_sha256"]="0"*64
        with self.assertRaises(ValueError):pack_numeric_report(r)
    def test_binary_sizes_are_fixed(self):
        self.assertEqual(EXPECTED_BYTES,164)
    def test_prevents_output_inside_public_source(self):
        source=Path(__file__).resolve().parents[1]
        with self.assertRaises(ValueError):
            output_private_only(source/"private"/"road.vprd")

if __name__=="__main__":
    unittest.main()
