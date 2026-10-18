"""Stage110 synthetic MMC3 midframe CHR bank switch and strict output validation."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from make_stage110_synthetic_midframe_rom import make_rom, program
from inject_fceux_stage110_raster_probe import patch_raster, CALL
from run_stage110_native_midframe import verify_report, MidframeError

MOCK = (
    b"vpd_ppu_probe::observe_native_bg_fetch(RefreshAddr, pt[0], false);\n"
    b"vpd_ppu_probe::observe_native_bg_fetch(RefreshAddr, pt[1], true);\n"
    b"\t\t\t\t\t\t\tvpd_ppu_probe::observe_native_bg_pixel(pixel & 3, *ptr);\n"
)
PASS = (
    "VPD_STAGE110_NATIVE_MIDFRAME_CHR_PASS writes=2 switch_sl={sl} "
    "pre_pixels=2048 post_pixels=2048 pre_zero={pre} post_three={post} "
    "pre_fnv64={ha} post_fnv64={hb} invalid={bad} "
    "same_native_frame=yes synthetic_only=yes original_game_raster_proven=no"
)


class ProbePatcher(unittest.TestCase):
    def test_append_raster_observer_once(self):
        s = patch_raster(MOCK)
        self.assertEqual(s.count(CALL), 1)
        self.assertIn(b"#ifdef VPD_NATIVE_SYNTHETIC_MIDFRAME_CHR", s)

    def test_refuse_unpinned_or_duplicate_source(self):
        for v in (MOCK + MOCK, MOCK.replace(b"observe_native_bg_pixel", b"other"),
                  patch_raster(MOCK)):
            with self.assertRaises(ValueError):
                patch_raster(v)

    def test_crlf_preservation(self):
        s = patch_raster(MOCK.replace(b"\n", b"\r\n"))
        self.assertEqual(s.count(b"\n"), s.count(b"\r\n"))


class RomTest(unittest.TestCase):
    def test_switch_rom_differs_by_one_repeated_bank_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.nes", Path(tmp) / "b.nes"
            make_rom(a, switch=True); make_rom(b, switch=False)
            raw, fixed = a.read_bytes(), b.read_bytes()
            self.assertEqual(len(raw), 49168)
            self.assertEqual(raw[:8], b"NES\x1a\x02\x02\x40\x00")
            self.assertEqual(raw[-16384:], fixed[-16384:])
            self.assertEqual(sum(x != y for x, y in zip(raw, fixed)), 4)
            self.assertIn(bytes((0x2c, 0x02, 0x20, 0x10, 0xfb)), program())

    def test_reject_bad_delay(self):
        for value in (0, 33, 256):
            with self.assertRaises(ValueError):
                program(delay_outer=value)


class MarkerAcceptance(unittest.TestCase):
    def test_accept_same_frame_distinct_final_pixel_windows(self):
        s = PASS.format(sl=100, pre=2048, post=2048, ha=123, hb=456, bad=0)
        v = verify_report(s)
        self.assertTrue(v["same_synthetic_frame_proven"])
        self.assertFalse(v["original_raster_proven"])

    def test_reject_false_pixel_claims(self):
        good = PASS.format(sl=100, pre=2048, post=2048, ha=123, hb=456, bad=0)
        for wrong in ("", good + "\n" + good,
                      good.replace("switch_sl=100", "switch_sl=0"),
                      good.replace("pre_zero=2048", "pre_zero=2047"),
                      good.replace("post_three=2048", "post_three=2047"),
                      good.replace("post_fnv64=456", "post_fnv64=123"),
                      good.replace("invalid=0", "invalid=1"),
                      good.replace("same_native_frame=yes", "same_native_frame=no"),
                      good.replace("original_game_raster_proven=no",
                                   "original_game_raster_proven=yes")):
            with self.subTest(text=wrong[:40]), self.assertRaises(MidframeError):
                verify_report(wrong)


@unittest.skipUnless(shutil.which("c++"), "C++ compiler missing")
class NativeCppTest(unittest.TestCase):
    def test_real_header_cxx11_midframe_switch(self):
        code = """#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main() {
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE", "1", 1);
 vpd_ppu_probe::stage110_register_write(2, 0);
 for(unsigned row=1;row<=100;++row)
  for(unsigned i=0;i<256;++i)
   vpd_ppu_probe::stage110_raster_pixel(row, 0, 15);
 vpd_ppu_probe::stage110_register_write(2, 1);
 for(unsigned row=101;row<=135;++row)
  for(unsigned i=0;i<256;++i)
   vpd_ppu_probe::stage110_raster_pixel(row, 3, 48);
 return 0;
}"""
        with tempfile.TemporaryDirectory() as folder:
            cpp, binary = Path(folder) / "s.cpp", Path(folder) / "s"
            cpp.write_text(code)
            build = subprocess.run(
                ["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror", "-pedantic",
                 "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR", "-I", str(ROOT / "tools"),
                 str(cpp), "-o", str(binary)], text=True, capture_output=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([str(binary)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(verify_report(result.stderr)["same_synthetic_frame_proven"])
            # Negative native control: identical framebuffer banks may not
            # publish the same success marker with invalid>0.
            cpp.write_text(code.replace("stage110_register_write(2, 1);",
                                        "stage110_register_write(2, 0);"))
            build = subprocess.run(
                ["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror", "-pedantic",
                 "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR", "-I", str(ROOT / "tools"),
                 str(cpp), "-o", str(binary)], text=True, capture_output=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            rejected = subprocess.run([str(binary)], text=True, capture_output=True)
            self.assertEqual(rejected.returncode, 0, rejected.stderr)
            self.assertNotIn("VPD_STAGE110_NATIVE_MIDFRAME_CHR_PASS", rejected.stderr)
            self.assertIn("VPD_STAGE110_REJECTED_CONTROL", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
