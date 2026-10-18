"""Stage100 NROM generation, proof-marker and negative-control regressions."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from make_stage100_synthetic_nrom import make_rom
from run_stage100_fceux_synthetic_smoke import inspect_output, SmokeError

MARKER = ("VPD_STAGE100_NEWPPU_RUNTIME_PASS raw_steps=8192 "
          "cycle_wraps=24 internal_label_changes=23 invalid_steps=0 "
          "zero_advance_calls=3 normalized_scanlines=no real_game_data=no")


class Stage100Tests(unittest.TestCase):
    def test_synthetic_nrom_has_known_program_and_null_chr(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "simple.nes"
            checksum = make_rom(path)
            payload = path.read_bytes()
            self.assertEqual(len(payload), 24592)
            self.assertEqual(payload[:6], b"NES\x1a\x01\x01")
            self.assertEqual(payload[16:24],
                             bytes((0xA9, 0x08, 0x8D, 1, 0x20, 0x4C, 5, 0xC0)))
            self.assertEqual(payload[-8192:], bytes(8192))
            self.assertEqual(make_rom(path), checksum)

    def test_accepts_single_aggregate_real_runtime_marker(self):
        result = inspect_output("starting\n" + MARKER + "\n",
                                expect_probe=True)
        self.assertEqual(result["steps"], 8192)
        self.assertEqual(result["zero_advance_calls"], 3)
        self.assertFalse(result["ntsc_raster_calibration_proven"])

    def test_missing_marker_rejected(self):
        with self.assertRaisesRegex(SmokeError, "Missing"):
            inspect_output("no hook callbacks", expect_probe=True)

    def test_legacy_renderer_must_not_emit_newppu_marker(self):
        self.assertIsNone(inspect_output("ordinary legacy execution",
                                         expect_probe=False))
        with self.assertRaisesRegex(SmokeError, "Legacy"):
            inspect_output(MARKER, expect_probe=False)

    def test_wrong_claim_or_malformed_line_rejected(self):
        with self.assertRaisesRegex(SmokeError, "malformed"):
            inspect_output(MARKER.replace("normalized_scanlines=no",
                                          "normalized_scanlines=yes"),
                           expect_probe=True)

    def test_zero_wrap_or_line_changes_rejected(self):
        for altered in (MARKER.replace("cycle_wraps=24", "cycle_wraps=0"),
                        MARKER.replace("internal_label_changes=23",
                                       "internal_label_changes=0")):
            with self.subTest(altered=altered), self.assertRaisesRegex(
                    SmokeError, "did not progress"):
                inspect_output(altered, expect_probe=True)

    def test_invalid_raw_counter_rejected(self):
        with self.assertRaisesRegex(SmokeError, "Invalid"):
            inspect_output(MARKER.replace("invalid_steps=0", "invalid_steps=1"),
                           expect_probe=True)

    def test_duplicate_markers_rejected(self):
        with self.assertRaisesRegex(SmokeError, "duplicate"):
            inspect_output(MARKER + "\n" + MARKER, expect_probe=True)


if __name__ == "__main__":
    unittest.main()
