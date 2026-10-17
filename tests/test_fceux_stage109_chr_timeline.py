"""Stage109 MMC3/source PPU clock chronology, acceptance, and C++11 hook tests."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from run_stage109_native_chr_timeline import TimelineError, verify_timeline

MARK = (
    "VPD_STAGE109_NATIVE_CHR_TIMELINE_PASS writes=1 fetches=8192 "
    "pixels=32768 bank={bank} first_fetch_lag={fetch} "
    "first_pixel_after_fetch_lag={pixel} last_pixel_after_write_lag={last} "
    "invalid={invalid} synthetic_only=yes original_game_timing_proven=no"
)


class Acceptance(unittest.TestCase):
    def test_accept_monotone_native_source_clock(self):
        for bank in (0, 1):
            result = verify_timeline(MARK.format(
                bank=bank, fetch=100, pixel=5, last=9000, invalid=0), bank=bank)
            self.assertTrue(result["source_clock_order_verified"])
            self.assertFalse(result["physical_raster_verified"])

    def test_refuse_forged_rom_claims_and_wrong_banks(self):
        valid = MARK.format(bank=0, fetch=100, pixel=5, last=9000, invalid=0)
        for invalid in (
            "", valid + "\n" + valid,
            valid.replace("writes=1", "writes=2"),
            valid.replace("fetches=8192", "fetches=8000"),
            valid.replace("pixels=32768", "pixels=32767"),
            valid.replace("bank=0", "bank=1"),
            valid.replace("invalid=0", "invalid=1"),
            valid.replace("original_game_timing_proven=no",
                          "original_game_timing_proven=yes"),
            valid.replace("first_fetch_lag=100", "first_fetch_lag=1000001"),
            valid.replace("last_pixel_after_write_lag=9000",
                          "last_pixel_after_write_lag=99"),
        ):
            with self.subTest(invalid=invalid[:50]), self.assertRaises(TimelineError):
                verify_timeline(invalid, bank=0)

    def test_coarse_clock_equal_tick_is_not_fake_hardware_precision(self):
        result = verify_timeline(MARK.format(
            bank=1, fetch=0, pixel=0, last=0, invalid=0), bank=1)
        self.assertTrue(result["source_clock_order_verified"])


@unittest.skipUnless(shutil.which("c++"), "C++ compiler unavailable")
class NativeHeader(unittest.TestCase):
    def compile_and_run(self, enabled=True, inverted=False):
        source = """#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main() {
    setenv("VPD_STAGE109_CHR_TIMELINE_PROBE", "%s", 1);
    vpd_ppu_probe::chr_chronology_write(2, %d);
    for(int n = 0; n < 8192; ++n) {
       vpd_ppu_probe::channel().internal_tick_units += 2;
       vpd_ppu_probe::chr_chronology_fetch(0x1000 + (n & 8), %d);
       for (int j=0; j<4; ++j) {
           ++vpd_ppu_probe::channel().internal_tick_units;
           vpd_ppu_probe::chr_chronology_pixel(%d);
       }
    }
    return 0;
}""" % (
            "1" if enabled else "0", 1, 0 if inverted else 255, 3)
        with tempfile.TemporaryDirectory() as folder:
            file, binary = Path(folder) / "chrono.cpp", Path(folder) / "chrono"
            file.write_text(source)
            proc = subprocess.run(
                ["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror", "-pedantic",
                 "-DVPD_NATIVE_SYNTHETIC_CHR_TIMELINE", "-I", str(ROOT / "tools"),
                 str(file), "-o", str(binary)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stderr

    def test_cxx_header_real_aggregate(self):
        result = self.compile_and_run()
        self.assertTrue(verify_timeline(result, bank=1)["source_clock_order_verified"])

    def test_native_invalid_fetch_detection(self):
        with self.assertRaises(TimelineError):
            verify_timeline(self.compile_and_run(inverted=True), bank=1)

    def test_disabled_timeline_must_not_emit(self):
        self.assertNotIn("VPD_STAGE109_NATIVE_CHR_TIMELINE_PASS",
                         self.compile_and_run(enabled=False))


if __name__ == "__main__":
    unittest.main()
