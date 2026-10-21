"""Synthetic-only MMC3 CHR register 0 diagnostic witness and RGB tests."""
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_private_chr_bank_ab import audit
from test_audit_private_chr_bank_ab import make_case


def make_chr0_case(root, *, frame=600, changed_frame=None):
    original, probe = make_case(root, frame=frame, changed_frame=changed_frame)
    for directory in (original, probe):
        file = directory / "COMPLETE.txt"
        contents = file.read_text(encoding="ascii")
        contents = contents.replace("private_chr_bank1_one_write_ab_v1",
                                    "private_chr_bank0_one_write_ab_v1")
        contents = contents.replace("probe_chr1_zero", "probe_chr0_two")
        contents = contents.replace("accumulator_restored_before_e38a",
                                    "cpu_x_restored_before_e383")
        file.write_text(contents, encoding="ascii")
    return original, probe


class OriginalChr0Tests(unittest.TestCase):
    def test_chr0_can_affect_next_frame_without_claiming_scanline(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = make_chr0_case(Path(directory), changed_frame=601)
            report = audit(a, b, frame=600, bank_register=0)
            self.assertEqual(report["mmc3_chr_register_number"], 0)
            self.assertEqual(report["cpu_write_pc"], "$E380")
            self.assertEqual(report["cpu_register_restored_at"], "$E383")
            self.assertEqual(report["counterfactual_mmc3_register_value"], "$02")
            self.assertEqual(report["frames"][2]["rgb_pixels_different"], 1)
            self.assertFalse(report["ppu_scanline_effect_verified"])

    def test_bank_zero_no_change_is_not_proof_of_inactivity(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = make_chr0_case(Path(directory))
            report = audit(a, b, frame=600, bank_register=0)
            self.assertTrue(report["all_captured_frames_identical"])
            self.assertFalse(report["effect_on_other_original_frames_proven_absent"])

    def test_chr0_rejects_chr1_capture_witness(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = make_case(Path(directory))
            with self.assertRaisesRegex(ValueError, "schema mismatch"):
                audit(a, b, frame=600, bank_register=0)

    def test_chr0_rejects_wrong_cpu_x_restoration(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = make_chr0_case(Path(directory))
            witness = b / "COMPLETE.txt"
            witness.write_text(witness.read_text("ascii").replace(
                "cpu_x_restored_before_e383=yes",
                "cpu_x_restored_before_e383=no"), encoding="ascii")
            with self.assertRaisesRegex(ValueError, "witness invalid"):
                audit(a, b, frame=600, bank_register=0)

    def test_rejects_unsupported_chr_register(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = make_chr0_case(Path(directory))
            with self.assertRaisesRegex(ValueError, "unsupported"):
                audit(a, b, frame=600, bank_register=2)


if __name__ == "__main__":
    unittest.main()
