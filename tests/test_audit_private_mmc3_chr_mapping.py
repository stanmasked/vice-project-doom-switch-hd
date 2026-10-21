"""Entirely invented register traces; no original emulator captures."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_mmc3_chr_mapping import analyze_trace,selected_banks

def fixture(root,lines):
    p=Path(root)/"mmc3_video_writes.tsv"
    p.write_text("frame\taddress\tvalue\n"+"\n".join(lines)+"\n",encoding="ascii")
    return p

class CHRMappingTraceTests(unittest.TestCase):
    def test_2k_even_alignment_selects_both_banks(self):
        with tempfile.TemporaryDirectory() as d:
            path=fixture(d,["7\t8000\t00","7\t8001\t7D"])
            r=analyze_trace(path)
            self.assertEqual([x["mapping_write_count"] for x in r["focus_bank_reports"]],[1,1,0])
            self.assertFalse(r["actual_ppu_rendered_bank_proven"])

    def test_reg2_1k_selection(self):
        with tempfile.TemporaryDirectory() as d:
            path=fixture(d,["1803\t8000\t02","1803\t8001\t7E"])
            r=analyze_trace(path)
            self.assertEqual([x["mapping_write_count"] for x in r["focus_bank_reports"]],[0,0,1])
            self.assertEqual(r["focus_bank_reports"][2]["candidate_movie_intervals"],[1])

    def test_r1_inversion_still_only_mapping_not_rendering(self):
        with tempfile.TemporaryDirectory() as d:
            path=fixture(d,["70\t8000\t41","70\t8001\t7C"])
            r=analyze_trace(path)
            self.assertEqual(r["inverted_chr_mode_writes"],1)
            self.assertEqual([x["mapping_write_count"] for x in r["focus_bank_reports"]],[1,1,0])
            self.assertFalse(r["original_stage_identity_proven"])

    def test_data_before_select_is_unattributed(self):
        with tempfile.TemporaryDirectory() as d:
            path=fixture(d,["1\t8001\t7C"])
            r=analyze_trace(path)
            self.assertEqual(r["unattributed_or_non_chr_data_writes"],1)
            self.assertEqual(r["valid_chr_mapping_data_writes"],0)

    def test_non_chr_register_is_not_interpreted(self):
        with tempfile.TemporaryDirectory() as d:
            path=fixture(d,["1\t8000\t06","1\t8001\t7C"])
            r=analyze_trace(path)
            self.assertEqual(r["unattributed_or_non_chr_data_writes"],1)
            self.assertFalse(any(b["mapping_write_count"] for b in r["focus_bank_reports"]))

    def test_duplicate_selects_count_but_do_not_prove_rendering(self):
        with tempfile.TemporaryDirectory() as d:
            path=fixture(d,["1\t8000\t02","1\t8001\t7C",
                            "2\t8000\t02","2\t8001\t7C"])
            r=analyze_trace(path)
            self.assertEqual(r["focus_bank_reports"][0]["mapping_write_count"],2)
            self.assertEqual(r["focus_bank_reports"][0]["first_mapping_frame"],1)
            self.assertEqual(r["focus_bank_reports"][0]["last_mapping_frame"],2)

    def test_wrong_trace_header_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"mmc3_video_writes.tsv"
            p.write_text("untrusted\n1\t8000\t02\n")
            with self.assertRaisesRegex(ValueError,"header"):
                analyze_trace(p)

    def test_chronology_regression_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=fixture(d,["9\t8000\t02","8\t8001\t7C"])
            with self.assertRaisesRegex(ValueError,"ordering regressed"):
                analyze_trace(path)

    def test_invalid_mapper_bank_count(self):
        with self.assertRaisesRegex(ValueError,"CHR bank count"):
            selected_banks(0,125,0)
        with self.assertRaisesRegex(ValueError,"CHR bank count"):
            analyze_trace("absent.tsv",bank_count=0)

    def test_overflow_wrap_and_dedup_2k_selection(self):
        self.assertEqual(selected_banks(0,255,128),(126,127))
        self.assertEqual(selected_banks(0,255,1),(0,))

    def test_target_outside_rom_bank_count_fails(self):
        with self.assertRaisesRegex(ValueError,"target banks"):
            analyze_trace("absent.tsv",bank_count=32,focus_banks=[124])

    def test_missing_file_and_symlink_fail(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"absent.tsv"
            with self.assertRaisesRegex(ValueError,"linked"):
                analyze_trace(p)
            target=fixture(d,["1\t8000\t00"])
            link=Path(d)/"alias.tsv"
            try:link.symlink_to(target)
            except OSError as exc:self.skipTest(str(exc))
            with self.assertRaisesRegex(ValueError,"linked"):
                analyze_trace(link)

if __name__=="__main__":
    unittest.main()
