"""Only wholly invented CHR tiles; no user's game images/ROM in CI."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_nes_variant_chr_tiles import inventory
from test_audit_private_nes_variant_banks import fake_rom

OFFSET=16+131072
TILE_BYTES=16


class OriginTests(unittest.TestCase):
    def pair(self,root,first,second):
        a=root/"first.nes";b=root/"second.nes"
        a.write_bytes(first);b.write_bytes(second)
        return inventory(a,b)

    def test_identical_tiles_across_header_versions(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.pair(Path(d),fake_rom(nes2=True),fake_rom())
            self.assertEqual(r["total_chr_tiles"],8192)
            self.assertEqual(r["same_offset_identical_tiles"],8192)
            self.assertEqual(r["modified_chr_bank_count"],0)
            self.assertFalse(r["level_geometry_proven"])

    def test_changed_tile_in_one_bank_not_in_other_rom(self):
        with tempfile.TemporaryDirectory() as d:
            first=bytearray(fake_rom());second=fake_rom()
            first[OFFSET+124*1024+0]=0x7e
            r=self.pair(Path(d),first,second)
            self.assertEqual(r["same_offset_modified_tiles"],1)
            item=r["modified_banks"][0]
            self.assertEqual(item["bank_index"],124)
            self.assertEqual(item["modified_global_tile_indices"],[124*64])
            self.assertEqual(item["first_changed_patterns_absent_anywhere_in_second"],1)

    def test_relocation_is_not_claimed_original_pattern(self):
        with tempfile.TemporaryDirectory() as d:
            first=bytearray(fake_rom())
            second=bytearray(fake_rom())
            # The nonblank invented pattern moves from tile 0 in first
            # to tile 1 in second: changed at both offsets but not novel.
            first[OFFSET+0]=0x7e
            second[OFFSET+16]=0x7e
            r=self.pair(Path(d),first,second)
            self.assertEqual(r["same_offset_modified_tiles"],2)
            self.assertEqual(r["first_modified_patterns_absent_anywhere_in_second"],0)
            self.assertEqual(r["second_modified_patterns_absent_anywhere_in_first"],0)

    def test_bank_blank_tile_counts(self):
        with tempfile.TemporaryDirectory() as d:
            first=bytearray(fake_rom());second=bytearray(fake_rom())
            for i in range(64):
                first[OFFSET+126*1024+i*16:OFFSET+126*1024+(i+1)*16]=bytes(16)
            r=self.pair(Path(d),first,second)
            item=next(x for x in r["modified_banks"] if x["bank_index"]==126)
            self.assertEqual(item["modified_tile_count"],64)
            self.assertEqual(item["first_version_zero_tiles"],64)
            self.assertEqual(item["second_version_zero_tiles"],0)

    def test_incompatible_mapper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);a=p/"one.nes";b=p/"two.nes"
            a.write_bytes(fake_rom(mapper=4))
            b.write_bytes(fake_rom(mapper=2))
            with self.assertRaisesRegex(ValueError,"mappers"):
                inventory(a,b)

    def test_differing_prg_does_not_change_chr_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            first=bytearray(fake_rom())
            first[16+100]=0x12
            r=self.pair(Path(d),first,fake_rom())
            self.assertEqual(r["same_offset_modified_tiles"],0)
            self.assertEqual(r["same_offset_identical_tiles"],8192)

    def test_all_modified_tile_indices_within_expected_range(self):
        with tempfile.TemporaryDirectory() as d:
            first=bytearray(fake_rom())
            first[OFFSET+8191*TILE_BYTES]=0x8f
            r=self.pair(Path(d),first,fake_rom())
            self.assertEqual(r["modified_banks"][0]["modified_global_tile_indices"],[8191])
            self.assertEqual(r["modified_banks"][0]["bank_index"],127)

if __name__=="__main__":
    unittest.main()
