"""Stage114 source CHR plane-pair validation: synthetic ROM, no hardware claim."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from inject_fceux_stage114_plane_pairs import inject_plane_pairs
from run_stage114_native_plane_pairs import (
    PlaneAuditError, verify_report,
)

SAMPLE = (b"vpd_ppu_probe::observe_native_bg_fetch(RefreshAddr, pt[0], false);\r\n"
          b"vpd_ppu_probe::observe_native_bg_fetch(RefreshAddr, pt[1], true);\r\n"
          b"\t\t\tpt[0] = CALL_PPUREAD(RefreshAddr);\r\n"
          b"\t\t\tpt[1] = CALL_PPUREAD(RefreshAddr);\r\n"
          b"vpd_ppu_probe::stage113_begin(sl, xt + 2);\r\n"
          b"vpd_ppu_probe::stage113_end(sl, xt + 2, "
          b"bgdata.main[xt + 2].pt[0], bgdata.main[xt + 2].pt[1]);\r\n"
          b"vpd_ppu_probe::stage113_draw(sl, xt, xp, bgtile, "
          b"bgdata.main[bgtile].pt[0], bgdata.main[bgtile].pt[1]);\r\n")
MARKER = (
    "VPD_STAGE114_NATIVE_PLANE_PAIR_PASS "
    "switch_sl=104 old_tiles=128 new_tiles=128 "
    "mixed_pairs=0 writes_between_planes=0 "
    "low_to_high_min=2 low_to_high_max=2 "
    "source_clock_only=yes pinned_fceux_only=yes "
    "synthetic_only=yes original_game_mixed_tiles_proven=no"
)
TILE = {"switch_source_scanline": 104, "first_new_xt": 5,
        "same_buffered_tile_frame_proven": True}
PREFETCH = {"switch_source_scanline": 104, "first_new_xt": 5,
            "original_game_prefetch_proven": False}


class Hook(unittest.TestCase):
    def test_guarded_pair_and_read_draw_sites(self):
        result = inject_plane_pairs(SAMPLE)
        for marker in (b"stage114_begin(", b"stage114_end(",
                       b"stage114_draw(", b"stage114_plane(0",
                       b"stage114_plane(1"):
            self.assertEqual(result.count(marker), 1)
        self.assertEqual(result.count(b"\n"), result.count(b"\r\n"))

    def test_reject_duplicated_reordered_and_partial_source(self):
        for raw in (SAMPLE + SAMPLE, inject_plane_pairs(SAMPLE),
                    SAMPLE.replace(b"pt[1] = CALL_PPUREAD", b"unknown"),
                    SAMPLE.replace(b"stage113_end", b"missing")):
            with self.subTest(raw=raw[:35]), self.assertRaises(ValueError):
                inject_plane_pairs(raw)

    def test_lf_line_endings_kept(self):
        lf = SAMPLE.replace(b"\r\n", b"\n")
        result = inject_plane_pairs(lf)
        self.assertNotIn(b"\r\n", result)


class Acceptance(unittest.TestCase):
    def test_valid_pinned_synthetic_no_mixed_observation(self):
        report = verify_report(MARKER, TILE, PREFETCH)
        self.assertEqual(report["mixed_pairs_observed"], 0)
        self.assertFalse(report["original_game_mixed_tiles_proven"])

    def test_refuse_claims_of_hardware_absence_or_missing_samples(self):
        for text in ("", MARKER + "\n" + MARKER,
                     MARKER.replace("mixed_pairs=0", "mixed_pairs=1"),
                     MARKER.replace("old_tiles=128", "old_tiles=127"),
                     MARKER.replace("writes_between_planes=0",
                                    "writes_between_planes=1"),
                     MARKER.replace("low_to_high_min=2", "low_to_high_min=0"),
                     MARKER.replace("low_to_high_max=2", "low_to_high_max=100"),
                     MARKER.replace("original_game_mixed_tiles_proven=no",
                                    "original_game_mixed_tiles_proven=yes")):
            with self.subTest(text=text[:45]), self.assertRaises(PlaneAuditError):
                verify_report(text, TILE, PREFETCH)
        with self.assertRaises(PlaneAuditError):
            verify_report(MARKER, {**TILE, "first_new_xt": 9}, PREFETCH)


@unittest.skipUnless(shutil.which("c++"), "C++ compiler unavailable")
class Cpp(unittest.TestCase):
    def test_cxx11_real_pair_observer_and_corruption_rejection(self):
        source = """#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main() {
 setenv("VPD_STAGE114_PLANE_PAIR_PROBE","1",1);
 vpd_ppu_probe::stage110_register_write(2,0);
 for(unsigned sl=1; sl<=112; ++sl) {
  for(unsigned xt=0;xt<32;++xt) {
   if(sl==104 && xt==1) vpd_ppu_probe::stage110_register_write(2,1);
   unsigned new_bank=sl>104 || (sl==104 && xt>=5);
   unsigned lo=new_bank?255:0;
   unsigned hi=new_bank?255:0;
   vpd_ppu_probe::stage114_begin(sl,xt+2);
   vpd_ppu_probe::stage114_plane(0,0x1000,lo);
   vpd_ppu_probe::channel().internal_tick_units+=2;
   vpd_ppu_probe::stage114_plane(1,0x1008,hi);
   vpd_ppu_probe::stage114_end(sl,xt+2,lo,hi);
   for(unsigned xp=0;xp<8;++xp) {
    vpd_ppu_probe::stage110_raster_pixel(sl,new_bank?3:0,new_bank?48:15);
    vpd_ppu_probe::stage114_draw(sl,xt,xp,xt,lo,hi);
    ++vpd_ppu_probe::channel().internal_tick_units;
   }
  }
 }
 return 0;
}"""
        with tempfile.TemporaryDirectory() as folder:
            cpp, exe = Path(folder) / "s.cpp", Path(folder) / "s"
            flags = ["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                     "-pedantic", "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                     "-DVPD_NATIVE_SYNTHETIC_BG_PLANE_PAIRS",
                     "-I", str(ROOT / "tools"), str(cpp), "-o", str(exe)]
            cpp.write_text(source)
            built = subprocess.run(flags, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            observed = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(observed.returncode, 0, observed.stderr)
            self.assertIn("VPD_STAGE114_NATIVE_PLANE_PAIR_PASS", observed.stderr)
            cpp.write_text(source.replace("unsigned hi=new_bank?255:0;",
                                          "unsigned hi=(new_bank?255:0) ^ (sl==104 && xt==4 ? 255 : 0);"))
            built = subprocess.run(flags, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            rejected = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertNotIn("VPD_STAGE114_NATIVE_PLANE_PAIR_PASS", rejected.stderr)
            self.assertIn("VPD_STAGE114_REJECTED_PLANE_PAIR", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
