"""Stage113 actual BGData.Read buffer-to-XBuf proof, guards and C++11."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from inject_fceux_stage113_prefetch_probe import (
    patch_prefetch, BEGIN, END, CONSUME,
)
from run_stage113_native_prefetch import (
    PrefetchError, verify_report, validate_prefetch_sweep,
)
from run_stage112_native_subscanline_sweep import PHASES

MOCK = (b"vpd_ppu_probe::observe_native_bg_fetch(RefreshAddr, pt[0], false);\n"
        b"vpd_ppu_probe::observe_native_bg_fetch(RefreshAddr, pt[1], true);\n"
        b"\t\t\t\tbgdata.main[xt + 2].Read();\n"
        b"\t\t\t\t\t\t\tvpd_ppu_probe::stage111_tile_pixel(sl, xt, xp, bgtile, "
        b"bgdata.main[bgtile].pt[0], "
        b"bgdata.main[bgtile].pt[1], pixel & 3);\n")
MARK = ("VPD_STAGE113_NATIVE_PREFETCH_PASS switch_sl={sl} "
        "first_new_sl={newsl} first_new_xt={xt} "
        "lookahead_tiles=2 matched_old=128 matched_new=128 "
        "old_after_write={old} old_prefetched_before={before} "
        "old_read_started_after={after} new_read_started_after=128 "
        "fetch_to_draw_min={lo} fetch_to_draw_max={hi} invalid=0 "
        "paired_tile_xbuf_frame=yes synthetic_only=yes "
        "original_game_prefetch_proven=no")


def tile(phase):
    idx = PHASES.index(phase)
    return {"switch_source_scanline": 104,
            "last_rendered_xt": 1 + 3 * idx,
            "first_new_source_scanline": 104,
            "first_new_xt": 5 + 3 * idx,
            "transient_old_tiles": 3,
            "same_buffered_tile_frame_proven": True,
            "original_game_tile_proven": False}


class Injection(unittest.TestCase):
    def test_real_read_begin_end_and_buffer_consumer_hook(self):
        output = patch_prefetch(MOCK)
        for call in (BEGIN, END, CONSUME):
            self.assertEqual(output.count(call), 1)
        self.assertIn(b"bgdata.main[xt + 2].pt[0]", output)
        self.assertIn(b"bgdata.main[bgtile].pt[0]", output)

    def test_reject_mismatched_sites_and_duplicate_patch(self):
        for raw in (MOCK + MOCK, patch_prefetch(MOCK),
                    MOCK.replace(b"bgdata.main[xt + 2].Read();", b"OTHER();"),
                    MOCK.replace(b"stage111_tile_pixel", b"unknown")):
            with self.subTest(case=raw[:60]), self.assertRaises(ValueError):
                patch_prefetch(raw)

    def test_crlf_pinned_fceux_source(self):
        output = patch_prefetch(MOCK.replace(b"\n", b"\r\n"))
        self.assertEqual(output.count(b"\r\n"), output.count(b"\n"))


class Acceptance(unittest.TestCase):
    def test_accepts_paired_native_read_origin_and_lags(self):
        witness = tile(0)
        report = MARK.format(sl=104, newsl=104, xt=5, old=3,
                             before=1, after=2, lo=12, hi=75)
        result = verify_report(report, witness)
        self.assertEqual(result["old_reads_started_after_switch"], 2)
        self.assertFalse(result["original_game_prefetch_proven"])

    def test_rejects_unbound_source_events_and_forged_hardware_precision(self):
        good = MARK.format(sl=104, newsl=104, xt=5, old=3,
                           before=1, after=2, lo=12, hi=75)
        bads = ("", good + "\n" + good,
                good.replace("matched_old=128", "matched_old=127"),
                good.replace("old_prefetched_before=1", "old_prefetched_before=9"),
                good.replace("fetch_to_draw_min=12", "fetch_to_draw_min=0"),
                good.replace("fetch_to_draw_max=75", "fetch_to_draw_max=2"),
                good.replace("first_new_xt=5", "first_new_xt=6"),
                good.replace("original_game_prefetch_proven=no",
                             "original_game_prefetch_proven=yes"))
        for wrong in bads:
            with self.subTest(text=wrong[:45]), self.assertRaises(PrefetchError):
                verify_report(wrong, tile(0))

    def test_phase_pairing_requires_all_four_matching_native_records(self):
        records = []
        for phase in PHASES:
            t = tile(phase)
            p = {"first_new_xt": t["first_new_xt"],
                 "first_new_source_scanline": 104,
                 "transient_old_tiles": 3,
                 "original_game_prefetch_proven": False}
            records.append((phase, t, p))
        validated, observed = validate_prefetch_sweep(records)
        self.assertEqual(len(observed), len(PHASES))
        self.assertEqual(validated["first_new_columns"], [5, 8, 11, 14])
        records[-1][2]["first_new_xt"] = 15
        with self.assertRaises(PrefetchError):
            validate_prefetch_sweep(records)


@unittest.skipUnless(shutil.which("c++"), "C++ compiler not present")
class NativeHeader(unittest.TestCase):
    def test_cpp11_native_fetch_then_draw_and_negative_corruption(self):
        sample = """#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main() {
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 setenv("VPD_STAGE111_BG_TILE_PROBE","1",1);
 setenv("VPD_STAGE113_BG_PREFETCH_PROBE","1",1);
 for (unsigned sl=1; sl<=120; ++sl) {
   for (unsigned xt=0; xt<32; ++xt) {
     if (sl==1 && xt==0) vpd_ppu_probe::stage110_register_write(2,0);
     if (sl==104 && xt==2) vpd_ppu_probe::stage110_register_write(2,1);
     unsigned fetchfull = sl>104 || (sl==104 && xt>=3);
     vpd_ppu_probe::stage113_begin(sl,xt+2);
     vpd_ppu_probe::channel().internal_tick_units+=8;
     vpd_ppu_probe::stage113_end(sl,xt+2,fetchfull?255:0,fetchfull?255:0);
     unsigned pixel = 0;
     if (xt>=2) {
       vpd_ppu_probe::PrefetchRecord &r =
         vpd_ppu_probe::stage113_state().records[xt];
       pixel=r.lo?3:0;
     } else {
       pixel=sl>104?3:0;
     }
     for(unsigned xp=0; xp<8; ++xp) {
       vpd_ppu_probe::stage110_raster_pixel(sl,pixel,pixel?48:15);
       vpd_ppu_probe::stage111_tile_pixel(sl,xt,xp,xt,pixel?255:0,
                                           pixel?255:0,pixel);
       vpd_ppu_probe::stage113_draw(sl,xt,xp,xt,pixel?255:0,pixel?255:0);
       vpd_ppu_probe::channel().internal_tick_units+=1;
     }
   }
 }
 return 0;
}"""
        with tempfile.TemporaryDirectory() as tmp:
            cpp, exe = Path(tmp) / "p.cpp", Path(tmp) / "p"
            flags = ["c++", "-std=c++11", "-Wall", "-Wextra",
                     "-Werror", "-pedantic",
                     "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                     "-DVPD_NATIVE_SYNTHETIC_BG_TILES",
                     "-DVPD_NATIVE_SYNTHETIC_BG_PREFETCH",
                     "-I", str(ROOT / "tools"),
                     str(cpp), "-o", str(exe)]
            cpp.write_text(sample)
            built = subprocess.run(flags, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            ran = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertIn("VPD_STAGE113_NATIVE_PREFETCH_PASS", ran.stderr)
            cpp.write_text(sample.replace(
                "fetchfull?255:0,fetchfull?255:0",
                "fetchfull?255:0,0"))
            built = subprocess.run(flags, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            ran = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertNotIn("VPD_STAGE113_NATIVE_PREFETCH_PASS", ran.stderr)


if __name__ == "__main__":
    unittest.main()
