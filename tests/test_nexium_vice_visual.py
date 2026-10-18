"""Independent fail-closed unit tests for actual NeXium screenshot auditor."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nexium_visual_audit", ROOT / "tools/audit_nexium_vice_visual.py"
)
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)


def fixture():
    # Synthetic PPM for AUDITOR testing only. Never treated as emulator proof.
    row = b"".join(bytes((x % 256, (x * 3) % 256, (x * 5) % 256))
                   for x in range(1280))
    first = row * 720
    second = bytearray(first)
    for pixel in range(0, len(first) // 3, 10):
        second[pixel * 3] ^= 0x55
    header = b"P6\n# comment from screenshot exporter\n1280 720\n255\n"
    return header + first, header + bytes(second)


class VisualAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a, cls.b = fixture()

    def test_dynamic_screen_passes(self):
        result = auditor.evaluate(self.a, self.b)
        self.assertGreater(result["changed"], 10)
        self.assertGreater(result["colored"], 100)
        self.assertEqual(len(result["before_sha256"]), 64)

    def test_blank_or_repeated_frame_cannot_pass(self):
        with self.assertRaisesRegex(ValueError, "unchanged"):
            auditor.evaluate(self.a, self.a)
        black = b"P6\n1280 720\n255\n" + bytes(1280 * 720 * 3)
        with self.assertRaisesRegex(ValueError, "blank"):
            auditor.evaluate(black, black)

    def test_truncated_or_forged_shape(self):
        invalid = [
            b"",
            self.a[:-1],
            self.a + b"x",
            self.a.replace(b"P6", b"P3", 1),
            self.a.replace(b"1280 720", b"1280 719", 1),
            self.a.replace(b"255", b"65535", 1),
            self.a.replace(b"1280 720", b"1280 720x", 1)
        ]
        for n, value in enumerate(invalid):
            with self.subTest(n=n), self.assertRaises(ValueError):
                auditor.evaluate(value, self.b)

    def test_never_accepts_synthetic_data_as_emulator_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "screen-before.ppm").write_bytes(self.a)
            (root / "screen-after.ppm").write_bytes(self.b)
            (root / "screen-before.png").write_bytes(b"test-only")
            (root / "screen-after.png").write_bytes(b"test-only")
            with self.assertRaisesRegex(ValueError, "did not finish"):
                auditor.audit_evidence(root)
            (root / "visual-probe.txt").write_text("visual_probe=finished\n")
            self.assertGreater(auditor.audit_evidence(root)["changed"], 10)
            (root / "screen-after.png").unlink()
            with self.assertRaisesRegex(ValueError, "PNG capture missing"):
                auditor.audit_evidence(root)


if __name__ == "__main__":
    unittest.main()
