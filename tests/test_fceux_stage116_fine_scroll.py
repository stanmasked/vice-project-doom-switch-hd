"""Stage116 $2005 fine-horizontal pixel-to-carried-tile provenance."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from make_stage110_synthetic_midframe_rom import make_rom, program
from inject_fceux_stage116_fine_scroll import (
    inject_fine_scroll, READ, DRAW,
)
from run_stage116_native_fine_scroll import (
    SCROLLS, FineScrollError, verify_report, validate_sweep,
)

MOCK = (b"vpd_ppu_probe::stage114_plane(0, RefreshAddr, pt[0]);\n"
        b"vpd_ppu_probe::stage114_plane(1, RefreshAddr, pt[1]);\n" +
        READ + b"\n" + DRAW + b"\n")
MARK = ("VPD_STAGE116_NATIVE_FINE_SCROLL_PASS fine_scroll={scroll} "
        "source_switch_sl=104 first_new_sl=105 "
        "samples=128 old_pixels=72 new_pixels=56 "
        "slot0_pixels={slot0} slot1_pixels={slot1} "
        "lag_min=21 lag_max=28 invalid=0 "
        "same_native_frame=yes synthetic_only=yes original_game_scroll_proven=no")


class GeneratedRom(unittest.TestCase):
    def test_zero_scroll_legacy_rom_unchanged(self):
        baseline = program()
        self.assertEqual(baseline, program(fine_scroll=0))

    def test_generated_scroll_writes_only_and_chr_banks_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            baseline = None
            for scroll in SCROLLS:
                path = Path(tmp) / ("%d.nes" % scroll)
                make_rom(path, fine_scroll=scroll)
                raw = path.read_bytes()
                self.assertEqual(len(raw), 49168)
                self.assertEqual(raw[:16], b"NES\x1a\x02\x02\x40" + bytes(9))
                if baseline is None:
                    baseline = raw
                self.assertEqual(raw[-16384:], baseline[-16384:])
                if scroll:
                    self.assertIn(bytes((0xa9, scroll, 0x8d, 5, 0x20,
                                         0xa9, 0, 0x8d, 5, 0x20)), raw)

    def test_reject_bad_fine_scroll_values(self):
        for v in (-1, 8, 300, 2.5, "2", True):
            with self.subTest(v=v), self.assertRaises(ValueError):
                program(fine_scroll=v)


class Instrumentation(unittest.TestCase):
    def test_guarded_real_record_read_and_draw_hooks(self):
        injected = inject_fine_scroll(MOCK)
        self.assertIn(b"stage116_edge_read", injected)
        self.assertIn(b"stage116_pixel", injected)
        self.assertIn(b"bgpx, ppur.fh", injected)

    def test_duplicate_unpinned_and_crlf_guard(self):
        for value in (MOCK + MOCK, inject_fine_scroll(MOCK),
                      MOCK.replace(READ, b"removed"),
                      MOCK.replace(DRAW, b"removed")):
            with self.assertRaises(ValueError):
                inject_fine_scroll(value)
        crlf = inject_fine_scroll(MOCK.replace(b"\n", b"\r\n"))
        self.assertEqual(crlf.count(b"\n"), crlf.count(b"\r\n"))


class Acceptance(unittest.TestCase):
    def test_all_four_horizontal_scroll_offsets(self):
        results = []
        for value in SCROLLS:
            text = MARK.format(scroll=value,
                               slot0=16 * (8-value), slot1=16*value)
            result = verify_report(text, value)
            results.append((value, result))
        self.assertEqual(validate_sweep(results)["slot1_counts"], [0, 16, 48, 112])

    def test_detect_modified_scroll_source_counts_or_forged_origin(self):
        valid = MARK.format(scroll=3, slot0=80, slot1=48)
        for corrupted in ("", valid + "\n" + valid,
                          valid.replace("slot0_pixels=80", "slot0_pixels=81"),
                          valid.replace("slot1_pixels=48", "slot1_pixels=47"),
                          valid.replace("first_new_sl=105", "first_new_sl=104"),
                          valid.replace("invalid=0", "invalid=1"),
                          valid.replace("original_game_scroll_proven=no",
                                        "original_game_scroll_proven=yes")):
            with self.subTest(case=corrupted[:32]), self.assertRaises(FineScrollError):
                verify_report(corrupted, 3)
        with self.assertRaises(FineScrollError):
            verify_report(valid, 7)


@unittest.skipUnless(shutil.which("c++"), "C++ compiler unavailable")
class HeaderTest(unittest.TestCase):
    def test_cpp11_native_scroll_per_pixel_for_each_phase_and_negative(self):
        source = """#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main(int argc,char**argv) {
 unsigned fine=argc>1?static_cast<unsigned>(argv[1][0]-'0'):3U;
 setenv("VPD_STAGE116_FINE_SCROLL_PROBE","1",1);
 char scroll[2] = {static_cast<char>('0'+fine),0};
 setenv("VPD_STAGE116_EXPECT_FINE_SCROLL",scroll,1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 vpd_ppu_probe::stage110_register_write(2,0);
 for(unsigned sl=95;sl<=111;++sl) {
  if(sl>=96) {
   for(unsigned xp=0;xp<8;++xp) {
    unsigned tile=(xp+fine)>>3;
    unsigned val=sl>=105?255U:0U;
    vpd_ppu_probe::stage116_pixel(sl,0,xp,tile,
      (xp+fine)&7,fine,val,val,sl>=105?3:0);
    vpd_ppu_probe::channel().internal_tick_units+=1;
   }
  }
  if(sl==104) {
   vpd_ppu_probe::stage110_state().last_sl=104;
   vpd_ppu_probe::stage110_state().pre=2048;
   vpd_ppu_probe::stage110_register_write(2,1);
  }
  if(sl<=110) {
   for(unsigned slot=0;slot<2;++slot) {
    unsigned v=sl>=104?255U:0U;
    vpd_ppu_probe::stage116_edge_read(sl,slot,v,v);
    vpd_ppu_probe::channel().internal_tick_units+=8;
   }
  }
  vpd_ppu_probe::channel().internal_tick_units+=100;
 }
 return 0;
}"""
        with tempfile.TemporaryDirectory() as td:
            cpp, exe = Path(td) / "f.cpp", Path(td) / "f"
            cpp.write_text(source)
            flags = ["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                     "-pedantic", "-DVPD_NATIVE_SYNTHETIC_FINE_SCROLL",
                     "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR", "-I",
                     str(ROOT / "tools"), str(cpp), "-o", str(exe)]
            built = subprocess.run(flags, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            for val in SCROLLS:
                run = subprocess.run([str(exe), str(val)],
                                     capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(verify_report(run.stderr, val)["slot1"],
                                 16 * val)
            cpp.write_text(source.replace(
                "(xp+fine)&7,fine,val,val,sl>=105?3:0);",
                "(xp+fine)&7,fine,val,val,0);"))
            built = subprocess.run(flags, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            run = subprocess.run([str(exe), "3"], capture_output=True, text=True)
            self.assertNotIn("VPD_STAGE116_NATIVE_FINE_SCROLL_PASS", run.stderr)
            self.assertIn("VPD_STAGE116_REJECTED_FINE_SCROLL", run.stderr)


if __name__ == "__main__":
    unittest.main()
