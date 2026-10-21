"""Only invented private MMC3 witness reports, no original NES ROM bytes."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_mmc3_chr_trace_witness import audit_trace_witness

VALID={
    "format":"private_mmc3_chr_trace_witness_v1",
    "movie_terminal_frame":"63",
    "raw_matching_mapping_writes":"500",
    "retained_deduplicated_mapping_pairs":"6",
    "suppressed_repeated_mapping_writes":"494",
    "trace_closed":"yes",
    "ppu_rendering_proven":"no"
}

def make(root,rows=None):
    d=VALID if rows is None else rows
    p=Path(root)/"private_mmc3.witness.txt"
    p.write_text("".join(f"{k}={v}\n" for k,v in d.items()),encoding="ascii")
    return p

class ClosedPrivateMMC3WitnessTests(unittest.TestCase):
    def verify(self,path,pairs=6,frame=63):
        return audit_trace_witness(path,expected_terminal_frame=frame,
                                   parsed_pair_count=pairs)

    def test_closed_valid_witness_separates_raw_and_retained(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.verify(make(d))
            self.assertEqual(r["raw_matching_mapping_writes"],500)
            self.assertEqual(r["suppressed_repeated_mapping_writes"],494)
            self.assertEqual(r["retained_deduplicated_mapping_pairs"],6)
            self.assertTrue(r["trace_closed"])
            self.assertFalse(r["actual_ppu_rendering_proven"])

    def test_empty_but_properly_closed_trace_is_inconclusive_on_presence(self):
        with tempfile.TemporaryDirectory() as d:
            rows=dict(VALID)
            rows.update(raw_matching_mapping_writes="0",
                        retained_deduplicated_mapping_pairs="0",
                        suppressed_repeated_mapping_writes="0")
            r=self.verify(make(d,rows),pairs=0)
            self.assertEqual(r["raw_matching_mapping_writes"],0)
            self.assertFalse(r["original_level_identity_proven"])

    def test_last_movie_frame_must_match(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"last movie frame"):
                self.verify(make(d),frame=64)

    def test_reject_count_discrepancy(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"pair count"):
                self.verify(make(d),pairs=5)

    def test_reject_inconsistent_raw_dedup_arithmetic(self):
        with tempfile.TemporaryDirectory() as d:
            rows=dict(VALID,suppressed_repeated_mapping_writes="493")
            with self.assertRaisesRegex(ValueError,"inconsistent"):
                self.verify(make(d,rows))

    def test_reject_unclosed_trace(self):
        with tempfile.TemporaryDirectory() as d:
            rows=dict(VALID,trace_closed="no")
            with self.assertRaisesRegex(ValueError,"unclosed"):
                self.verify(make(d,rows))

    def test_reject_claim_that_data_was_rendered(self):
        with tempfile.TemporaryDirectory() as d:
            rows=dict(VALID,ppu_rendering_proven="yes")
            with self.assertRaisesRegex(ValueError,"PPU rendering"):
                self.verify(make(d,rows))

    def test_reject_truncated_sidecar(self):
        with tempfile.TemporaryDirectory() as d:
            rows={k:v for k,v in VALID.items() if k!="movie_terminal_frame"}
            with self.assertRaisesRegex(ValueError,"missing"):
                self.verify(make(d,rows))

    def test_reject_duplicate_fields(self):
        with tempfile.TemporaryDirectory() as d:
            p=make(d)
            with p.open("a",encoding="ascii") as stream:
                stream.write("trace_closed=yes\n")
            with self.assertRaisesRegex(ValueError,"duplicate"):
                self.verify(p)

    def test_refuse_symlinked_sidecar(self):
        with tempfile.TemporaryDirectory() as d:
            origin=make(d)
            alias=Path(d)/"linked.witness"
            try: alias.symlink_to(origin)
            except OSError as exc: self.skipTest(str(exc))
            with self.assertRaisesRegex(ValueError,"missing or invalid"):
                self.verify(alias)

    def test_reject_noncanonical_numeric_field(self):
        with tempfile.TemporaryDirectory() as d:
            rows=dict(VALID,raw_matching_mapping_writes="000500")
            with self.assertRaisesRegex(ValueError,"numeric"):
                self.verify(make(d,rows))

    def test_reject_oversized_summary(self):
        with tempfile.TemporaryDirectory() as d:
            p=make(d)
            with p.open("a",encoding="ascii") as stream:
                stream.write("A"*3000)
            with self.assertRaisesRegex(ValueError,"missing or invalid"):
                self.verify(p)

if __name__=="__main__":
    unittest.main()
