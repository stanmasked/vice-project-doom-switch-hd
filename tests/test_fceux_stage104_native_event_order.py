"""Stage104 native source event ordering: ROM-free C++ and parser checks."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from run_stage104_native_event_order import verify_timeline, EventOrderError

ROOT = Path(__file__).resolve().parents[1]
MARKER = ("VPD_STAGE104_NATIVE_EVENT_ORDER_PASS reads=16384 "
          "source_entries=3 source_clears=2 "
          "high_reads=2 high_read_clears=2 high_within_window=2 "
          "low_after_high=1234 high_lag_min=12 high_lag_max=87 invalid=0 "
          "source_timeline_only=yes physical_vblank_proven=no")


class NativeEventOrderTests(unittest.TestCase):
    def test_valid_synthetic_marker_is_source_only(self):
        r = verify_timeline(MARKER)
        self.assertEqual(r["high_cpu_reads"], 2)
        self.assertEqual(r["source_status_entries"], 3)
        self.assertTrue(r["source_event_order_verified"])
        self.assertFalse(r["hardware_ppu_vblank_proven"])
        self.assertFalse(r["original_level_geometry_proven"])

    def test_final_frame_may_have_unmatched_enter(self):
        r = verify_timeline(
            MARKER.replace("source_entries=3 source_clears=2",
                           "source_entries=3 source_clears=3"))
        self.assertEqual(r["source_status_clears"], 3)

    def test_missing_duplicate_or_forged_marker_refused(self):
        for value in (
            "",
            MARKER + "\n" + MARKER,
            MARKER.replace("source_timeline_only=yes", "source_timeline_only=no"),
            MARKER.replace("physical_vblank_proven=no", "physical_vblank_proven=yes"),
            MARKER.replace("reads=16384", "reads=128"),
        ):
            with self.subTest(value=value[:48]), self.assertRaises(EventOrderError):
                verify_timeline(value)

    def test_unpaired_source_windows_rejected(self):
        for value in (
            MARKER.replace("source_entries=3", "source_entries=1"),
            MARKER.replace("source_clears=2", "source_clears=0"),
            MARKER.replace("source_clears=2", "source_clears=5"),
        ):
            with self.subTest(value=value[:48]), self.assertRaises(EventOrderError):
                verify_timeline(value)

    def test_high_read_requires_source_window_and_clear(self):
        for value in (
            MARKER.replace("high_reads=2", "high_reads=0"),
            MARKER.replace("high_read_clears=2", "high_read_clears=1"),
            MARKER.replace("high_within_window=2", "high_within_window=1"),
            MARKER.replace("high_reads=2", "high_reads=5"),
        ):
            with self.subTest(value=value[:48]), self.assertRaises(EventOrderError):
                verify_timeline(value)

    def test_followup_low_reads_required(self):
        with self.assertRaisesRegex(EventOrderError, "follow-up"):
            verify_timeline(MARKER.replace("low_after_high=1234",
                                           "low_after_high=0"))

    def test_invalid_monotonic_lags_rejected(self):
        for old, new in (
            ("high_lag_min=12", "high_lag_min=99"),
            ("high_lag_max=87", "high_lag_max=1000001"),
        ):
            with self.subTest(new=new), self.assertRaises(EventOrderError):
                verify_timeline(MARKER.replace(old, new))

    def test_explicit_invalid_counter_rejected(self):
        with self.assertRaisesRegex(EventOrderError, "inconsistency"):
            verify_timeline(MARKER.replace("invalid=0", "invalid=2"))


@unittest.skipUnless(shutil.which("c++"), "C++ compiler unavailable")
class CompiledEventOrderTests(unittest.TestCase):
    def compile_and_run(self, *, enabled=True, corrupt=False):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            source = folder / "event_order.cpp"
            source.write_text(
                '#include "vpd_newppu_raw_step_probe.h"\n'
                '#include <cstdlib>\n'
                '#include <cassert>\n'
                'int main() {\n'
                f'  assert(setenv("VPD_STAGE104_EVENT_ORDER_PROBE", '
                f'"{1 if enabled else 0}", 1) == 0);\n'
                '  vpd_ppu_probe::channel().internal_tick_units = 10;\n'
                '  vpd_ppu_probe::observe_native_status_assignment(true, true);\n'
                '  for (int i = 0; i < 16384; ++i) {\n'
                '    if (i == 2048 || i == 8192 || i == 14336) {\n'
                '      vpd_ppu_probe::channel().internal_tick_units += 90000;\n'
                '      if (i != 2048) {\n'
                '        vpd_ppu_probe::observe_native_status_assignment(false, false);\n'
                '      }\n'
                '      if (i != 14336) {\n'
                '        vpd_ppu_probe::channel().internal_tick_units += 1;\n'
                '        vpd_ppu_probe::observe_native_status_assignment(true, true);\n'
                '      }\n'
                '    }\n'
                '    bool high = (i == 100 || i == 2300 || i == 8250);\n'
                '    bool bad = high && i == 2300;\n'
                f'    vpd_ppu_probe::observe_native_ppustatus_read(high, high, '
                f'{"bad" if corrupt else "false"});\n'
                '  }\n'
                '  return 0;\n'
                '}\n'
            )
            binary = folder / "candidate"
            command = [
                "c++", "-std=c++11", "-Wall", "-Wextra", "-pedantic", "-Werror",
                "-DVPD_NATIVE_SYNTHETIC_EVENT_ORDER",
                "-DVPD_NATIVE_SYNTHETIC_VBLANK",
                "-DVPD_NATIVE_SYNTHETIC_PPUSTATUS_READ",
                "-I", str(ROOT / "tools"), str(source), "-o", str(binary),
            ]
            build = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            exe = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(exe.returncode, 0, exe.stderr)
            return exe.stderr

    def test_header_compiles_and_produces_valid_aggregate(self):
        content = self.compile_and_run()
        proof = verify_timeline(content)
        self.assertGreater(proof["high_cpu_reads"], 0)

    def test_opt_out_emits_no_timeline(self):
        content = self.compile_and_run(enabled=False)
        self.assertNotIn("VPD_STAGE104_NATIVE_EVENT_ORDER_PASS", content)

    def test_invalid_bit_after_read_fails_closed(self):
        content = self.compile_and_run(corrupt=True)
        with self.assertRaises(EventOrderError):
            verify_timeline(content)


if __name__ == "__main__":
    unittest.main()
