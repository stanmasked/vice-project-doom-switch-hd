"""Stage101 Xvfb vs dummy backend and sanitized process-exit regressions."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from run_stage100_fceux_synthetic_smoke import (
    backend_settings, categorize_exit, inspect_output, SmokeError,
)


class HeadlessDiagnosticsTests(unittest.TestCase):
    def test_dummy_selects_qt_offscreen_sdl_dummy(self):
        with tempfile.TemporaryDirectory() as temp:
            env = backend_settings("dummy", Path(temp))
        self.assertEqual(env["QT_QPA_PLATFORM"], "offscreen")
        self.assertEqual(env["SDL_VIDEODRIVER"], "dummy")
        self.assertEqual(env["SDL_AUDIODRIVER"], "dummy")
        self.assertNotIn("QT_OPENGL", env)
        self.assertNotIn("LIBGL_ALWAYS_SOFTWARE", env)

    def test_xvfb_selects_xcb_and_sdl_x11(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"DISPLAY": ":91"}):
                env = backend_settings("xvfb", Path(temp))
        self.assertEqual(env["QT_QPA_PLATFORM"], "xcb")
        self.assertEqual(env["SDL_VIDEODRIVER"], "x11")
        self.assertEqual(env["LIBGL_ALWAYS_SOFTWARE"], "1")

    def test_xvfb_without_display_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(SmokeError, "without display"):
                    backend_settings("xvfb", Path(temp))

    def test_reject_unknown_backend(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            backend_settings("fake", Path("."))

    def test_segfault_categorized_without_raw_data(self):
        self.assertEqual(categorize_exit(-11, "private ROM /home/foo"),
                         "signal_sigsegv")
        self.assertEqual(categorize_exit(139, ""), "signal_sigsegv")

    def test_abort_categorized_without_raw_data(self):
        self.assertEqual(categorize_exit(-6, "user secret path"),
                         "signal_sigabrt")
        self.assertEqual(categorize_exit(134, ""), "signal_sigabrt")

    def test_qt_plugin_failure_categorized(self):
        self.assertEqual(categorize_exit(
            1, "Could not load the Qt platform plugin xcb from private path"),
            "qt_platform_initialization")

    def test_sdl_failure_categorized(self):
        self.assertEqual(categorize_exit(
            1, "Could not initialize SDL: dummy driver"),
            "sdl_initialization")

    def test_unknown_exit_and_normal_termination_distinguished(self):
        self.assertEqual(categorize_exit(2, "game secret"),
                         "other_early_process_exit")
        for code in (None, 0, -15):
            with self.subTest(code=code):
                self.assertEqual(categorize_exit(code, ""),
                                 "not_an_early_failure")

    def test_disabled_probe_must_never_emit_positive_marker(self):
        marker = ("VPD_STAGE100_NEWPPU_RUNTIME_PASS raw_steps=8192 "
                  "cycle_wraps=24 internal_label_changes=28 invalid_steps=0 "
                  "zero_advance_calls=4 normalized_scanlines=no real_game_data=no")
        with self.assertRaisesRegex(SmokeError, "unexpectedly"):
            inspect_output(marker, expect_probe=False)
        self.assertIsNone(inspect_output("headless start", expect_probe=False))


if __name__ == "__main__":
    unittest.main()
