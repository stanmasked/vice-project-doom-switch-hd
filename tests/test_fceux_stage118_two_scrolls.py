"""Stage118: two native $2005 writes (fine and coarse), bounded evidence."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from make_stage110_synthetic_midframe_rom import program, make_rom
from inject_fceux_stage118_two_scrolls import inject_two_scrolls, WRITE, PIXEL
from run_stage118_native_two_scrolls import (
    FINES, TwoScrollError, verify_report, verify_sweep,
)

PINNED = (
    b"vpd_ppu_probe::stage110_raster_pixel(sl, pixel & 3, *ptr);\r\n"
    b"vpd_ppu_probe::stage116_pixel(sl, xt, xp, bgtile, bgpx, ppur.fh, "
    b"bgdata.main[bgtile].pt[0], bgdata.main[bgtile].pt[1], pixel & 3);\r\n"
    + WRITE + b"\r\n" + PIXEL + b"\r\n"
)

MARK = (
    "VPD_STAGE118_NATIVE_TWO_SCROLL_PASS "
    "first_fine={fine} second_fine={second} "
    "coarse_first=0 coarse_second=1 "
    "first_sl=104 first_x=38 second_sl=105 second_x=99 "
    "first_after_x=39 second_after_x=100 "
    "first_pixels=64 second_pixels=64 next_pixels=16 "
    "shifted_first=64 shifted_second=64 "
    "same_synthetic_frame=yes source_clock_only=yes "
    "original_game_coarse_scroll_proven=no"
)


def good(fine):
    return MARK.format(fine=fine, second=8-fine)


class Rom(unittest.TestCase):
    def test_legacy_single_write_program_is_unchanged(self):
        self.assertEqual(program(), program(second_dynamic_scroll=None))
        for f in FINES:
            self.assertEqual(
                program(dynamic_fine_scroll=f),
                program(dynamic_fine_scroll=f, second_dynamic_scroll=None),
            )

    def test_both_cpu_x_y_pairs_and_same_chr_across_variants(self):
        with tempfile.TemporaryDirectory() as folder:
            chr_reference = None
            for first in FINES:
                path = Path(folder) / ("%d.nes" % first)
                make_rom(path, dynamic_fine_scroll=first,
                         second_dynamic_scroll=16-first)
                data = path.read_bytes()
                self.assertEqual(len(data), 49168)
                if chr_reference is None:
                    chr_reference = data[-16384:]
                self.assertEqual(data[-16384:], chr_reference)
                self.assertIn(bytes((0xa9, first, 0x8d, 5, 0x20,
                                     0xa9, 0, 0x8d, 5, 0x20)),
                              data)
                self.assertIn(bytes((0xa2, 28, 0xca, 0xd0, 0xfd,
                                     0xa9, 16-first, 0x8d, 5, 0x20,
                                     0xa9, 0, 0x8d, 5, 0x20)),
                              data)
                # Four banks of the same generated PRG, four writes per bank.
                self.assertEqual(data.count(bytes((0x8d, 5, 0x20))), 16)

    def test_reject_out_of_sequence_or_noncoarse_second_write(self):
        for f, second in ((None, 15), (1, 11), (3, 5), (5, 9),
                          (7, 8), (3, 16), (3, 3), (3, 13.1),
                          (3, True)):
            with self.subTest(first=f, second=second), self.assertRaises(ValueError):
                program(dynamic_fine_scroll=f, second_dynamic_scroll=second)


class Injection(unittest.TestCase):
    def test_pinned_write_and_render_site_injection(self):
        injected = inject_two_scrolls(PINNED)
        self.assertEqual(injected.count(b"stage118_write("), 1)
        self.assertEqual(injected.count(b"stage118_pixel("), 1)
        self.assertEqual(injected.count(b"\n"), injected.count(b"\r\n"))

    def test_reject_wrong_duplicate_or_reordered_sources(self):
        for sample in (PINNED + PINNED, inject_two_scrolls(PINNED),
                       PINNED.replace(WRITE, b"removed"),
                       PINNED.replace(PIXEL, b"removed"),
                       PINNED.replace(b"stage116_pixel", b"wrong")):
            with self.subTest(sample=sample[:32]), self.assertRaises(ValueError):
                inject_two_scrolls(sample)


class Marker(unittest.TestCase):
    def test_validate_four_native_scroll_pairs(self):
        trials = [(f, verify_report(good(f), f)) for f in FINES]
        self.assertEqual(verify_sweep(trials)["second_line"], 105)

    def test_reject_bad_registers_raster_and_origins(self):
        valid = good(3)
        for s in ("", valid + "\n" + valid,
                  valid.replace("coarse_second=1", "coarse_second=0"),
                  valid.replace("second_fine=5", "second_fine=3"),
                  valid.replace("second_sl=105", "second_sl=104"),
                  valid.replace("second_x=99", "second_x=255"),
                  valid.replace("first_after_x=39", "first_after_x=75"),
                  valid.replace("second_after_x=100", "second_after_x=85"),
                  valid.replace("next_pixels=16", "next_pixels=15"),
                  valid.replace("original_game_coarse_scroll_proven=no",
                                "original_game_coarse_scroll_proven=yes")):
            with self.subTest(s=s[:35]), self.assertRaises(TwoScrollError):
                verify_report(s, 3)
        with self.assertRaises(TwoScrollError):
            verify_report(valid, 3, xbuf={
                "switch_source_scanline": 105,
                "same_synthetic_frame_proven": True,
                "original_raster_proven": False
            })


@unittest.skipUnless(shutil.which("c++"), "C++ compiler unavailable")
class Cxx(unittest.TestCase):
    def test_real_header_two_writes_and_corrupt_coarse_rejected(self):
        code = """#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main(int argc,char**argv) {
 unsigned fine=argc>1?static_cast<unsigned>(argv[1][0]-'0'):3U;
 char env[]={static_cast<char>('0'+fine),0};
 setenv("VPD_STAGE118_TWO_SCROLL_PROBE","1",1);
 setenv("VPD_STAGE118_FIRST_FINE",env,1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 vpd_ppu_probe::stage110_register_write(2,0);
 for(unsigned sl=1;sl<=110;++sl) {
  for(unsigned x=0;x<256;++x) {
   if(sl==104 && x==36)
     vpd_ppu_probe::stage110_register_write(2,1);
   if(sl==104 && x==39)
     vpd_ppu_probe::stage118_write(fine,0);
   if(sl==105 && x==100)
     vpd_ppu_probe::stage118_write(8-fine,1);
   unsigned nowfine=sl>105||(sl==105&&x>=100)?
       8-fine : (sl>104||(sl==104&&x>=39)?fine:0U);
   unsigned pos=x+nowfine;
   unsigned filled=sl>=105||(sl==104&&x>=48);
   unsigned value=filled?255U:0U;
   vpd_ppu_probe::stage118_pixel(sl,x/8,x%8,pos>>3,pos&7,nowfine,
                                  value,value,filled?3:0);
   vpd_ppu_probe::stage110_raster_pixel(sl,filled?3:0,filled?48:15);
   ++vpd_ppu_probe::channel().internal_tick_units;
  }
 }
 return 0;
}"""
        with tempfile.TemporaryDirectory() as tmp:
            src, exe = Path(tmp) / "sample.cpp", Path(tmp) / "sample"
            args = ["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                    "-pedantic", "-DVPD_NATIVE_SYNTHETIC_TWO_SCROLLS",
                    "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                    "-I", str(ROOT / "tools"), str(src), "-o", str(exe)]
            src.write_text(code)
            built = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            for fine in FINES:
                ran = subprocess.run([str(exe), str(fine)],
                                     capture_output=True, text=True)
                self.assertEqual(ran.returncode, 0, ran.stderr)
                result = verify_report(ran.stderr, fine)
                self.assertEqual(result["second_source_scanline"], 105)
            src.write_text(code.replace(
                "stage118_write(8-fine,1);", "stage118_write(8-fine,0);"))
            compiled = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            bad = subprocess.run([str(exe), "3"], capture_output=True, text=True)
            self.assertNotIn("VPD_STAGE118_NATIVE_TWO_SCROLL_PASS", bad.stderr)
            self.assertIn("VPD_STAGE118_REJECTED_TWO_SCROLLS", bad.stderr)


if __name__ == "__main__":
    unittest.main()
