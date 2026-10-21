"""Synthetic-only tests for exact private FCEUX transition analysis."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_private_fceux_storyboard import P6_HEADER, PAL_SIZE
from audit_private_fceux_transition import audit_transition
from test_audit_private_fceux_storyboard import capture

BLACK_P6 = P6_HEADER + b"\x00" * (PAL_SIZE * 3)


def make_window(root, black=(3, 4, 5), stop=8):
    root.mkdir()
    for frame in range(1, stop + 1):
        capture(root, frame, interval=1, start=1, stop=stop, limit=stop)
        if frame in black:
            (root / ("frame_%06d.ppm" % frame)).write_bytes(BLACK_P6)
    return root


class ExactTransitionTests(unittest.TestCase):
    def test_one_exact_black_interval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = make_window(Path(directory) / "source")
            report = audit_transition(root, minimum_black_frames=3)
            self.assertEqual(report["last_visible_frame_before_black"], 2)
            self.assertEqual(report["first_black_frame"], 3)
            self.assertEqual(report["last_black_frame"], 5)
            self.assertEqual(report["first_visible_frame_after_black"], 6)
            self.assertEqual(report["black_frame_count"], 3)
            self.assertTrue(report["storyboard_complete"])
            self.assertFalse(report["named_stage_identity_proven_by_this_analyzer"])

    def test_cross_session_rgb_and_palette_byte_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = make_window(root / "source")
            comparison = root / "comparison"
            comparison.mkdir()
            for frame in (2, 4, 6, 8):
                capture(comparison, frame, interval=2, start=2, stop=8, limit=4)
                for ext in (".ppm", ".pal.bin"):
                    name = "frame_%06d%s" % (frame, ext)
                    (comparison / name).write_bytes((source / name).read_bytes())
            report = audit_transition(source, compare=comparison)
            self.assertEqual(report["overlapping_frames_verified"], 4)
            self.assertTrue(report["rgb_palette_pairs_identical"])

    def test_reject_different_rom_identity_between_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = make_window(root / "source")
            comparison = root / "comparison"
            comparison.mkdir()
            capture(comparison, 2, interval=2, start=2, stop=2, limit=1,
                    rom="a" * 32)
            for ext in (".ppm", ".pal.bin"):
                name = "frame_000002" + ext
                (comparison / name).write_bytes((source / name).read_bytes())
            with self.assertRaisesRegex(ValueError, "ROM identity"):
                audit_transition(source, compare=comparison)

    def test_reject_modified_second_session(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = make_window(root / "source")
            comparison = root / "comparison"
            comparison.mkdir()
            capture(comparison, 2, interval=2, start=2, stop=2, limit=1)
            ppm = comparison / "frame_000002.ppm"
            raw = bytearray(ppm.read_bytes())
            raw[-1] = 9
            ppm.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "not byte-identical"):
                audit_transition(source, compare=comparison)

    def test_reject_missing_image_in_exact_window(self):
        with tempfile.TemporaryDirectory() as directory:
            root = make_window(Path(directory) / "source")
            for ext in (".ppm", ".pal.bin", ".meta.txt"):
                (root / ("frame_000004" + ext)).unlink()
            with self.assertRaisesRegex(ValueError, "window incomplete"):
                audit_transition(root)

    def test_reject_multiple_separate_black_intervals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = make_window(Path(directory) / "source", black=(3, 4, 7))
            with self.assertRaisesRegex(ValueError, "unambiguous"):
                audit_transition(root)

    def test_reject_black_interval_without_visible_end(self):
        with tempfile.TemporaryDirectory() as directory:
            root = make_window(Path(directory) / "source", black=(6, 7, 8))
            with self.assertRaisesRegex(ValueError, "unambiguous"):
                audit_transition(root)

    def test_reject_insufficient_black_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            root = make_window(Path(directory) / "source")
            with self.assertRaisesRegex(ValueError, "unambiguous"):
                audit_transition(root, minimum_black_frames=4)

    def test_reject_non_unit_capture_interval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            for frame in (2, 4, 6):
                capture(root, frame, interval=2, start=2, stop=6, limit=3)
            with self.assertRaisesRegex(ValueError, "one image per movie frame"):
                audit_transition(root)


if __name__ == "__main__":
    unittest.main()
