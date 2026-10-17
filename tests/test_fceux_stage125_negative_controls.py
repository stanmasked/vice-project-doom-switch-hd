"""Stage125: fail-closed native negative-control rejection provenance."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from run_stage124_native_quadrants import (
    QuadrantNativeError, verify, verify_rejection, execute,
)

ATTR = (
    "VPD_STAGE124_REJECTED_QUADRANTS invalid=48 "
    "bad_attribute=64 bad_color=48 colors=176,176,176,176 "
    "samples=16,16,16,16 synthetic_only=yes"
)
PALETTE = (
    "VPD_STAGE124_REJECTED_QUADRANTS invalid=48 "
    "bad_attribute=0 bad_color=48 colors=176,176,176,176 "
    "samples=16,16,16,16 synthetic_only=yes"
)
PASS = (
    "VPD_STAGE124_NATIVE_QUADRANTS_PASS groups=4 "
    "samples=16,16,16,16 indices=3,7,11,15 "
    "xbuf_colors=176,177,178,179 raw_attribute=E4 invalid=0 "
    "actual_fceux_xbuf=yes synthetic_only=yes "
    "original_game_palette_proven=no"
)


class NativeNegativeCertificates(unittest.TestCase):
    def test_attribute_and_palette_causal_rejection_distinct(self):
        a = verify_rejection(ATTR, "attribute")
        p = verify_rejection(PALETTE, "palette")
        self.assertEqual(a["bad_attribute"], 64)
        self.assertEqual(p["bad_attribute"], 0)
        self.assertGreater(a["bad_color"], 0)
        self.assertGreater(p["bad_color"], 0)
        self.assertEqual(a["xbuf_colors"], [176] * 4)
        self.assertTrue(a["native_rejection_observed"])
        self.assertTrue(p["native_rejection_observed"])
        self.assertRaises(QuadrantNativeError, verify, ATTR)
        self.assertRaises(QuadrantNativeError, verify, PALETTE)

    def test_fail_closed_missing_duplicate_forged_or_wrong_cause(self):
        mutations = (
            ("", "attribute"),
            (ATTR + "\n" + ATTR, "attribute"),
            (ATTR + "\n" + PASS, "attribute"),
            (ATTR.replace("invalid=48", "invalid=0"), "attribute"),
            (ATTR.replace("bad_attribute=64", "bad_attribute=0"), "attribute"),
            (ATTR.replace("bad_color=48", "bad_color=0"), "attribute"),
            (ATTR.replace("176,176,176,176", "176,177,176,176"), "attribute"),
            (ATTR.replace("samples=16,16,16,16",
                          "samples=16,16,15,16"), "attribute"),
            (ATTR.replace("synthetic_only=yes", "synthetic_only=no"), "attribute"),
            (ATTR, "palette"),
            (PALETTE, "attribute"),
            (PALETTE.replace("bad_color=48", "bad_color=0"), "palette"),
            (PALETTE.replace("bad_attribute=0", "bad_attribute=1"), "palette"),
        )
        for report, cause in mutations:
            with self.subTest(report=report[-85:], cause=cause):
                with self.assertRaises(QuadrantNativeError):
                    verify_rejection(report, cause)

    def test_invalid_rejection_modes_rejected_before_process_start(self):
        with self.assertRaises(ValueError):
            execute(Path("nonexistent"), Path("nonexistent"), Path("unused"),
                    positive=True, expect_rejection="attribute")
        with self.assertRaises(ValueError):
            execute(Path("nonexistent"), Path("nonexistent"), Path("unused"),
                    enabled=False, positive=False, expect_rejection="palette")
        with self.assertRaises(ValueError):
            execute(Path("nonexistent"), Path("nonexistent"), Path("unused"),
                    positive=False, expect_rejection="unrecognized")

if __name__ == "__main__":
    unittest.main()
