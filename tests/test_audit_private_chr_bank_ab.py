"""Synthetic-only CHR-register A/B screenshot provenance tests."""
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_private_chr_bank_ab import audit, PIXELS, HEADER


def make_case(root, *, frame=600, changed_frame=None, change_pal=True):
    original = root / "original"
    probe = root / "probe"
    original.mkdir()
    probe.mkdir()
    for directory, mode in ((original, "original"),
                            (probe, "probe_chr1_zero")):
        witness = {
            "format": "private_chr_bank1_one_write_ab_v1",
            "mode": mode,
            "target_frame": str(frame),
            "first_observed_frame": "1",
            "last_observed_frame": str(frame + 2),
            "frame_gaps": "0",
            "writer_pc_hits": "1",
            "next_instruction_hits": "1",
            "accumulator_restored_before_e38a":
                "yes" if mode == "probe_chr1_zero" else "not_needed",
            "rom_payload_md5": "b" * 32,
            "fm2_readonly": "yes",
        }
        (directory / "COMPLETE.txt").write_text(
            "".join(f"{key}={value}\n" for key, value in witness.items()),
            encoding="ascii")
        for n in range(frame - 1, frame + 3):
            rgb = bytearray(b"\x30" * PIXELS * 3)
            palette = bytearray(b"\x0f" * PIXELS)
            if mode == "probe_chr1_zero" and n == changed_frame:
                rgb[(100 * 256 + 80) * 3] = 0xee
                if change_pal:
                    palette[100 * 256 + 80] = 0x09
            name = f"frame_{n:06d}"
            (directory / (name + ".ppm")).write_bytes(HEADER + rgb)
            (directory / (name + ".pal.bin")).write_bytes(palette)
    return original, probe


class OriginalChrBankTests(unittest.TestCase):
    def test_no_difference_does_not_claim_chr_bank_inactive(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_case(Path(d))
            result = audit(a, b, frame=600)
            self.assertTrue(result["all_captured_frames_identical"])
            self.assertFalse(result["visible_rgb_difference_observed"])
            self.assertFalse(result["ppu_chr_mapping_proven_identical"])
            self.assertFalse(result["effect_on_other_original_frames_proven_absent"])
            self.assertFalse(result["ppu_scanline_effect_verified"])
            self.assertEqual([f["frame"] for f in result["frames"]], [599, 600, 601, 602])
            self.assertNotIn(d, str(result))

    def test_changed_single_pixel_in_following_frame(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_case(Path(d), changed_frame=601)
            result = audit(a, b, frame=600)
            self.assertFalse(result["all_captured_frames_identical"])
            self.assertEqual(result["frames"][2]["rgb_pixels_different"], 1)
            self.assertEqual(result["frames"][2]["palette_indices_different"], 1)
            self.assertEqual(result["frames"][2]["affected_row_indices"], [100])

    def test_palette_only_difference_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_case(Path(d), changed_frame=601, change_pal=False)
            result = audit(a, b, frame=600)
            self.assertEqual(result["frames"][2]["rgb_pixels_different"], 1)
            self.assertEqual(result["frames"][2]["palette_indices_different"], 0)
            self.assertFalse(result["frames"][2]["rgb_palette_row_counts_match"])

    def test_pre_intervention_divergence_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_case(Path(d), changed_frame=599)
            with self.assertRaisesRegex(ValueError, "before"):
                audit(a, b, frame=600)

    def test_unrestored_accumulator_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_case(Path(d))
            witness = b / "COMPLETE.txt"
            witness.write_text(witness.read_text("ascii").replace(
                "accumulator_restored_before_e38a=yes",
                "accumulator_restored_before_e38a=no"), encoding="ascii")
            with self.assertRaisesRegex(ValueError, "witness invalid"):
                audit(a, b, frame=600)

    def test_wrong_rom_identity_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_case(Path(d))
            witness = b / "COMPLETE.txt"
            witness.write_text(witness.read_text("ascii").replace(
                "b" * 32, "a" * 32), encoding="ascii")
            with self.assertRaisesRegex(ValueError, "different original ROM"):
                audit(a, b, frame=600)

    def test_missing_rgb_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_case(Path(d))
            (b / "frame_000601.ppm").unlink()
            with self.assertRaisesRegex(ValueError, "missing"):
                audit(a, b, frame=600)

    def test_wrong_size_image_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_case(Path(d))
            image = b / "frame_000600.ppm"
            image.write_bytes(image.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, "malformed"):
                audit(a, b, frame=600)

    def test_duplicate_witness_field_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_case(Path(d))
            with (b / "COMPLETE.txt").open("a", encoding="ascii") as file:
                file.write("mode=original\n")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                audit(a, b, frame=600)

    def test_symlinked_capture_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_case(Path(d))
            link = Path(d) / "copy"
            try:
                link.symlink_to(b, target_is_directory=True)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(ValueError, "symlinked"):
                audit(a, link, frame=600)


if __name__ == "__main__":
    unittest.main()
