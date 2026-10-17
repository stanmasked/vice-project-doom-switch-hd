"""Stage115 next-line BGData two-tile buffer carry and strict witness acceptance."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from inject_fceux_stage115_edge_carry import (
    inject_edge_carry, READ_CALL, DRAW_CALL,
)
from run_stage115_native_scanline_carry import (
    CarryError, verify_report,
)

SOURCE = (
    b"vpd_ppu_probe::stage113_draw(sl, xt, xp, bgtile, bgdata.main[bgtile].pt[0], "
    b"bgdata.main[bgtile].pt[1]);\r\n"
    b"vpd_ppu_probe::stage114_plane(0, RefreshAddr, pt[0]);\r\n"
    b"vpd_ppu_probe::stage114_plane(1, RefreshAddr, pt[1]);\r\n"
    b"\t\t\tfor (int xt = 0; xt < 2; xt++)\r\n"
    b"\t\t\t\tbgdata.main[xt].Read();\r\n"
    b"\t\t\t\t\t\t\tvpd_ppu_probe::stage114_draw(sl, xt, xp, bgtile, "
    b"bgdata.main[bgtile].pt[0], bgdata.main[bgtile].pt[1]);\r\n"
)
MARKER = (
    "VPD_STAGE115_NATIVE_EDGE_CARRY_PASS switch_sl=104 "
    "observed_lines=16 edge_tiles=32 old_tiles=18 new_tiles=14 "
    "first_new_sl=105 fine_scroll=0 carry_lag_min={low} "
    "carry_lag_max={high} invalid=0 same_synthetic_frame=yes "
    "original_game_scroll_proven=no"
)
TILE = {"switch_source_scanline": 104, "same_buffered_tile_frame_proven": True}
PLANE = {"source_sl": 104, "mixed_pairs_observed": 0}


class SourceHook(unittest.TestCase):
    def test_two_tile_loop_stays_inside_braces(self):
        result = inject_edge_carry(SOURCE)
        self.assertEqual(result.count(READ_CALL), 1)
        self.assertEqual(result.count(DRAW_CALL), 1)
        self.assertIn(b"for (int xt = 0; xt < 2; xt++) {", result)
        self.assertIn(b"vpd_ppu_probe::stage115_edge_read", result)
        self.assertEqual(result.count(b"\r\n"), result.count(b"\n"))

    def test_reject_double_patch_wrong_source_and_ambiguous_loop(self):
        for raw in (SOURCE + SOURCE, inject_edge_carry(SOURCE),
                    SOURCE.replace(b"xt < 2", b"xt < 3"),
                    SOURCE.replace(b"stage114_draw", b"missing")):
            with self.subTest(source=raw[:36]), self.assertRaises(ValueError):
                inject_edge_carry(raw)

    def test_preserve_lf(self):
        self.assertNotIn(b"\r\n", inject_edge_carry(
            SOURCE.replace(b"\r\n", b"\n")))


class Acceptance(unittest.TestCase):
    def test_valid_cross_scanline_native_witness(self):
        record = verify_report(MARKER.format(low=240, high=258), TILE, PLANE)
        self.assertEqual(record["old_tiles"], 18)
        self.assertEqual(record["first_new_edge_line"], 105)
        self.assertFalse(record["original_game_scroll_proven"])

    def test_enabled_native_subprobes_do_not_skip_carry_marker_gate(self):
        runner = (ROOT / "tools" / "run_stage111_native_tile_boundary.py").read_text()
        self.assertIn("if prefetch or plane_pairs or scanline_carry:", runner)
        self.assertIn("VPD_STAGE115_DIAGNOSTIC", runner)
        self.assertNotIn("return witness, output\n    if plane_pairs:", runner)

    def test_reject_forged_or_cross_frame_claims(self):
        valid = MARKER.format(low=240, high=258)
        for text in ("", valid + "\n" + valid,
                     valid.replace("observed_lines=16", "observed_lines=15"),
                     valid.replace("old_tiles=18", "old_tiles=17"),
                     valid.replace("fine_scroll=0", "fine_scroll=3"),
                     valid.replace("first_new_sl=105", "first_new_sl=104"),
                     valid.replace("carry_lag_min=240", "carry_lag_min=0"),
                     valid.replace("carry_lag_max=258", "carry_lag_max=1"),
                     valid.replace("original_game_scroll_proven=no",
                                   "original_game_scroll_proven=yes")):
            with self.subTest(text=text[:48]), self.assertRaises(CarryError):
                verify_report(text, TILE, PLANE)
        with self.assertRaises(CarryError):
            verify_report(valid, {**TILE, "switch_source_scanline": 103}, PLANE)


@unittest.skipUnless(shutil.which("c++"), "C++ compiler unavailable")
class NativeHeader(unittest.TestCase):
    def test_cpp11_actual_header_carry_and_corrupt_negative(self):
        source = """#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main() {
 setenv("VPD_STAGE115_SCANLINE_CARRY_PROBE","1",1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 vpd_ppu_probe::stage110_register_write(2,0);
 for(unsigned sl=95;sl<=111;++sl) {
   if(sl>=96) {
     for(unsigned xt=0;xt<2;++xt) {
       unsigned val=sl>=105?255:0;
       vpd_ppu_probe::stage115_edge_draw(sl,xt,0,xt,0,val,val);
       vpd_ppu_probe::channel().internal_tick_units+=16;
     }
   }
   if(sl==104) {
     vpd_ppu_probe::stage110_state().last_sl=104;
     vpd_ppu_probe::stage110_state().pre=2048;
     vpd_ppu_probe::stage110_register_write(2,1);
   }
   if(sl<=110) {
     for(unsigned xt=0;xt<2;++xt) {
       unsigned val=sl>=104?255:0;
       vpd_ppu_probe::stage115_edge_read(sl,xt,val,val);
       vpd_ppu_probe::channel().internal_tick_units+=8;
     }
   }
   vpd_ppu_probe::channel().internal_tick_units+=100;
 }
 return 0;
}"""
        with tempfile.TemporaryDirectory() as temp:
            cpp, exe = Path(temp) / "edge.cpp", Path(temp) / "edge"
            flags = ["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                     "-pedantic", "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                     "-DVPD_NATIVE_SYNTHETIC_SCANLINE_CARRY",
                     "-I", str(ROOT / "tools"), str(cpp), "-o", str(exe)]
            cpp.write_text(source)
            build = subprocess.run(flags, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("VPD_STAGE115_NATIVE_EDGE_CARRY_PASS", result.stderr)
            cpp.write_text(source.replace(
                "unsigned val=sl>=105?255:0;",
                "unsigned val=sl>=105?255:0; if(sl==105 && xt==0) val=0;"))
            build = subprocess.run(flags, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            corrupted = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(corrupted.returncode, 0, corrupted.stderr)
            self.assertNotIn("VPD_STAGE115_NATIVE_EDGE_CARRY_PASS", corrupted.stderr)
            self.assertIn("VPD_STAGE115_REJECTED_EDGE_CARRY", corrupted.stderr)


if __name__ == "__main__":
    unittest.main()
