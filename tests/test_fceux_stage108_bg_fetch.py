"""Synthetic stage108 direct BG pattern fetch provenance and strict marker gates."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from inject_fceux_stage108_bg_fetch_probe import patch_bg_fetch, CALL
from run_stage108_native_bg_fetch import (
    verify_fetch, verify_pair, FetchProofError,
)
from run_stage107_native_bg_pixels import verify_report as verify_pixels

SOURCE = (
    b'#include "vpd_newppu_raw_step_probe.h"\n'
    b'vpd_ppu_probe::observe_native_bg_pixel(pixel & 3, *ptr);\n'
    b'\t\t\t\tpt[0] = CALL_PPUREAD(RefreshAddr);\n'
    b'\t\t\t\tpt[1] = CALL_PPUREAD(RefreshAddr);\n'
)
FETCH = (
    "VPD_STAGE108_NATIVE_BG_FETCH_PASS reads=8192 low=4096 high=4096 "
    "zero={zero} ff={ff} other={other} paired=4096 invalid={invalid} "
    "synthetic_only=yes original_game_fetch_proven=no"
)
PIXEL = (
    "VPD_STAGE107_NATIVE_BG_PIXEL_PASS sampled=32768 "
    "bg_zero={zero} bg_nonzero={nonzero} final_fnv64={hash} invalid=0 "
    "synthetic_only=yes original_pixel_proof=no"
)


class HookTests(unittest.TestCase):
    def test_exact_two_pattern_planes(self):
        s = patch_bg_fetch(SOURCE)
        self.assertEqual(s.count(CALL), 2)
        self.assertIn(b"RefreshAddr, pt[0], false", s)
        self.assertIn(b"RefreshAddr, pt[1], true", s)
        self.assertEqual(s.count(b"if (ScreenON)"), 2)

    def test_fail_closed_missing_ambiguous_and_double_patch(self):
        candidates = (
            SOURCE + SOURCE, SOURCE.replace(b"pt[1]", b"pt[2]"),
            SOURCE.replace(b"pt[0]", b"pt[3]"),
            SOURCE.replace(b"observe_native_bg_pixel", b"other_function"),
            patch_bg_fetch(SOURCE),
        )
        for src in candidates:
            with self.subTest(s=src[:60]), self.assertRaises(ValueError):
                patch_bg_fetch(src)

    def test_preserve_crlf_patched_source(self):
        raw = patch_bg_fetch(SOURCE.replace(b"\n", b"\r\n"))
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"))


class NativeWitnessTests(unittest.TestCase):
    def test_pair_must_include_actual_pixel_hash_difference(self):
        blank = verify_fetch(FETCH.format(zero=8192, ff=0, other=0, invalid=0))
        full = verify_fetch(FETCH.format(zero=0, ff=8192, other=0, invalid=0))
        a = verify_pixels(PIXEL.format(zero=32768, nonzero=0, hash=123))
        b = verify_pixels(PIXEL.format(zero=0, nonzero=32768, hash=456))
        self.assertTrue(verify_pair(blank, full, a, b)["synthetic_chr_fetch_and_pixels_proven"])
        with self.assertRaises(FetchProofError):
            verify_pair(blank, full, a, verify_pixels(
                PIXEL.format(zero=0, nonzero=32768, hash=123)))

    def test_malformed_duplicate_and_nonpairing_rejected(self):
        expected = FETCH.format(zero=8192, ff=0, other=0, invalid=0)
        for bad in ("", expected + "\n" + expected,
                    expected.replace("invalid=0", "invalid=1"),
                    expected.replace("other=0", "other=1"),
                    expected.replace("reads=8192", "reads=8000"),
                    expected.replace("paired=4096", "paired=0"),
                    expected.replace("original_game_fetch_proven=no",
                                     "original_game_fetch_proven=yes")):
            with self.subTest(text=bad[:50]), self.assertRaises(FetchProofError):
                verify_fetch(bad)

    def test_neither_bank_may_sneak_in_mixed_fetches(self):
        a = verify_pixels(PIXEL.format(zero=32768, nonzero=0, hash=1))
        b = verify_pixels(PIXEL.format(zero=0, nonzero=32768, hash=2))
        for zero, ff in ((7500, 692), (4000, 4192)):
            mixed = verify_fetch(FETCH.format(zero=zero, ff=ff, other=0, invalid=0))
            full = verify_fetch(FETCH.format(zero=0, ff=8192, other=0, invalid=0))
            with self.assertRaises(FetchProofError):
                verify_pair(mixed, full, a, b)


@unittest.skipUnless(shutil.which("c++"), "Native C++ compiler unavailable")
class HeaderRuntime(unittest.TestCase):
    def test_compile_cxx11_and_verify_real_hook_pairing(self):
        code = """#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main() {
  setenv("VPD_STAGE108_BG_FETCH_PROBE", "1", 1);
  for(int i=0;i<4096;++i) {
    vpd_ppu_probe::observe_native_bg_fetch(0x1000, 0xFF, false);
    vpd_ppu_probe::observe_native_bg_fetch(0x1008, 0xFF, true);
  }
  return 0;
}"""
        with tempfile.TemporaryDirectory() as folder:
            src, exe = Path(folder) / "fetch.cpp", Path(folder) / "fetch"
            src.write_text(code)
            build = subprocess.run(
                ["c++", "-std=c++11", "-Wall", "-Wextra", "-pedantic", "-Werror",
                 "-DVPD_NATIVE_SYNTHETIC_BG_FETCH", "-I", str(ROOT / "tools"),
                 str(src), "-o", str(exe)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            proof = verify_fetch(result.stderr)
            self.assertEqual(proof["ff"], 8192)


if __name__ == "__main__":
    unittest.main()
