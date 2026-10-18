"""Stage111 guarded tile-buffer provenance and same-frame XBuf controls."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from inject_fceux_stage111_tile_probe import patch_tile_probe, CALL
from run_stage111_native_tile_boundary import verify_report, TileProofError

MOCK = (b"vpd_ppu_probe::observe_native_bg_fetch(RefreshAddr, pt[0], false);\n"
        b"vpd_ppu_probe::observe_native_bg_fetch(RefreshAddr, pt[1], true);\n"
        b"vpd_ppu_probe::stage110_raster_pixel(sl, pixel & 3, *ptr);\n")
MARKER = ("VPD_STAGE111_NATIVE_TILE_BOUNDARY_PASS switch_sl={sl} "
          "last_rendered_xt={xt} pre_tiles=128 pre_zero=128 "
          "transient_old={old} first_new_sl={firstsl} first_new_xt={firstxt} "
          "new_tiles=128 new_ff=128 regressions=0 invalid=0 "
          "same_rendered_frame=yes synthetic_only=yes original_game_tile_proven=no")


class Hook(unittest.TestCase):
    def test_reads_rendered_buffer_both_pattern_planes(self):
        output = patch_tile_probe(MOCK)
        self.assertEqual(output.count(CALL), 1)
        self.assertIn(b"bgdata.main[bgtile].pt[0]", output)
        self.assertIn(b"bgdata.main[bgtile].pt[1]", output)

    def test_reject_duplicate_and_unsupported_sites(self):
        for source in (MOCK + MOCK, patch_tile_probe(MOCK),
                       MOCK.replace(b"stage110_raster_pixel", b"foo"),
                       MOCK.replace(b"observe_native_bg_fetch", b"bar")):
            with self.subTest(source=source[:30]), self.assertRaises(ValueError):
                patch_tile_probe(source)

    def test_crlf_preserved(self):
        output = patch_tile_probe(MOCK.replace(b"\n", b"\r\n"))
        self.assertEqual(output.count(b"\n"), output.count(b"\r\n"))


class Marker(unittest.TestCase):
    def test_same_frame_bound_to_stage110_witness(self):
        text = MARKER.format(sl=104, xt=14, old=2, firstsl=104, firstxt=19)
        result = verify_report(text, stage110={
            "switch_source_scanline": 104,
            "same_synthetic_frame_proven": True})
        self.assertTrue(result["same_buffered_tile_frame_proven"])
        self.assertFalse(result["original_game_tile_proven"])

    def test_missing_forged_and_cross_frame_markers_rejected(self):
        text = MARKER.format(sl=104, xt=14, old=2, firstsl=104, firstxt=19)
        cases = ("", text + "\n" + text,
                 text.replace("pre_zero=128", "pre_zero=127"),
                 text.replace("new_ff=128", "new_ff=127"),
                 text.replace("regressions=0", "regressions=1"),
                 text.replace("invalid=0", "invalid=1"),
                 text.replace("transient_old=2", "transient_old=65"),
                 text.replace("first_new_sl=104", "first_new_sl=110"),
                 text.replace("last_rendered_xt=14", "last_rendered_xt=33"),
                 text.replace("original_game_tile_proven=no",
                              "original_game_tile_proven=yes"))
        for s in cases:
            with self.subTest(s=s[:40]), self.assertRaises(TileProofError):
                verify_report(s)
        with self.assertRaises(TileProofError):
            verify_report(text, stage110={
                "switch_source_scanline": 105,
                "same_synthetic_frame_proven": True})


@unittest.skipUnless(shutil.which("c++"), "C++ compiler unavailable")
class Native(unittest.TestCase):
    def test_cpp11_original_header_accepts_and_rejects_buffer_bytes(self):
        source = """#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main() {
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE", "1", 1);
 setenv("VPD_STAGE111_BG_TILE_PROBE", "1", 1);
 vpd_ppu_probe::stage110_register_write(2, 0);
 for(unsigned sl=1;sl<=104;++sl)
  for(unsigned xt=0;xt<32;++xt)
   for(unsigned xp=0;xp<8;++xp) {
    vpd_ppu_probe::stage110_raster_pixel(sl, 0, 15);
    vpd_ppu_probe::stage111_tile_pixel(sl,xt,xp,xt,0,0,0);
   }
 vpd_ppu_probe::stage110_register_write(2, 1);
 for(unsigned sl=105;sl<=130;++sl)
  for(unsigned xt=0;xt<32;++xt)
   for(unsigned xp=0;xp<8;++xp) {
    vpd_ppu_probe::stage110_raster_pixel(sl,3,48);
    vpd_ppu_probe::stage111_tile_pixel(sl,xt,xp,xt,255,255,3);
   }
 return 0;
}"""
        with tempfile.TemporaryDirectory() as tmp:
            cpp, exe = Path(tmp) / "sample.cpp", Path(tmp) / "sample"
            flags = ["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                     "-pedantic", "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                     "-DVPD_NATIVE_SYNTHETIC_BG_TILES",
                     "-I", str(ROOT / "tools"), str(cpp), "-o", str(exe)]
            cpp.write_text(source)
            compiled = subprocess.run(flags, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(
                verify_report(run.stderr)["first_new_source_scanline"], 105)
            cpp.write_text(source.replace(
                "stage111_tile_pixel(sl,xt,xp,xt,255,255,3);",
                "stage111_tile_pixel(sl,xt,xp,xt,0,0,3);"))
            compiled = subprocess.run(flags, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            bad = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(bad.returncode, 0, bad.stderr)
            self.assertNotIn("VPD_STAGE111_NATIVE_TILE_BOUNDARY_PASS", bad.stderr)


if __name__ == "__main__":
    unittest.main()
