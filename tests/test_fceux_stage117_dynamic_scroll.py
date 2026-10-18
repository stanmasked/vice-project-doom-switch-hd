"""Stage117 runtime $2005 changes and real raster-source provenance tests."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from make_stage110_synthetic_midframe_rom import program, make_rom
from inject_fceux_stage117_dynamic_scroll import inject_dynamic_scroll
from run_stage117_native_dynamic_scroll import (
    VALUES, DynamicScrollError, verify_report, verify_sweep,
)

REGISTER = b"\t\tppur.fh = V & 7;"
DRAW = (b"vpd_ppu_probe::stage116_pixel(sl, xt, xp, bgtile, bgpx, ppur.fh, "
        b"bgdata.main[bgtile].pt[0], bgdata.main[bgtile].pt[1], pixel & 3);")
SOURCE = (b"vpd_ppu_probe::stage110_raster_pixel(sl, pixel & 3, *ptr);\r\n"
          b"vpd_ppu_probe::stage115_edge_draw(sl, xt, xp, bgtile, ppur.fh, "
          b"bgdata.main[bgtile].pt[0], bgdata.main[bgtile].pt[1]);\r\n"
          + REGISTER + b"\r\n" + DRAW + b"\r\n")
MARKER = (
    "VPD_STAGE117_NATIVE_DYNAMIC_SCROLL_PASS old_fine=0 new_fine={fine} "
    "write_sl=104 write_x=16 first_after_x=17 "
    "same_line_samples=64 next_line_samples=16 shifted_samples=64 "
    "first_lag=12 source_clock_only=yes same_native_frame=yes "
    "synthetic_only=yes original_game_midframe_scroll_proven=no"
)


def example(fine):
    return MARKER.format(fine=fine)


class CpuROM(unittest.TestCase):
    def test_existing_rom_unchanged_by_opt_in_extension(self):
        self.assertEqual(program(), program(dynamic_fine_scroll=None))
        with tempfile.TemporaryDirectory() as folder:
            first = Path(folder) / "first.nes"
            second = Path(folder) / "second.nes"
            make_rom(first)
            make_rom(second, dynamic_fine_scroll=None)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_real_midframe_cpu_writes_and_chr_data_stable(self):
        with tempfile.TemporaryDirectory() as folder:
            original = None
            for target in VALUES:
                rom = Path(folder) / ("%d.nes" % target)
                make_rom(rom, dynamic_fine_scroll=target)
                contents = rom.read_bytes()
                self.assertEqual(len(contents), 49168)
                if original is None:
                    original = contents
                self.assertEqual(contents[-16384:], original[-16384:])
                self.assertIn(bytes((0xa9, target, 0x8d, 5, 0x20,
                                     0xa9, 0, 0x8d, 5, 0x20)), contents)
                self.assertEqual(contents.count(bytes((0x8d, 5, 0x20))), 8)

    def test_invalid_scroll_values_rejected(self):
        for target in (0, 2, 4, 6, 8, -1, 1.5, "3", True):
            with self.subTest(target=target), self.assertRaises(ValueError):
                program(dynamic_fine_scroll=target)
        with self.assertRaises(ValueError):
            program(fine_scroll=3, dynamic_fine_scroll=5)


class FceuxInjection(unittest.TestCase):
    def test_guarded_register_write_and_final_xbuf_sink(self):
        modified = inject_dynamic_scroll(SOURCE)
        self.assertEqual(modified.count(b"stage117_scroll_write("), 1)
        self.assertEqual(modified.count(b"stage117_pixel("), 1)
        self.assertEqual(modified.count(b"\n"), modified.count(b"\r\n"))

    def test_reject_unsupported_double_or_ambiguous_hooks(self):
        for raw in (SOURCE + SOURCE, inject_dynamic_scroll(SOURCE),
                    SOURCE.replace(REGISTER, b"removed"),
                    SOURCE.replace(DRAW, b"removed"),
                    SOURCE.replace(b"stage110_raster_pixel", b"removed")):
            with self.subTest(sample=raw[:35]), self.assertRaises(ValueError):
                inject_dynamic_scroll(raw)


class Witness(unittest.TestCase):
    def test_accepted_native_phase_records(self):
        entries = []
        for fine in VALUES:
            info = verify_report(example(fine), fine)
            self.assertFalse(info["original_game_midframe_scroll_proven"])
            entries.append((fine, info))
        self.assertEqual(verify_sweep(entries)["source_sl"], 104)

    def test_reject_missing_duplicate_and_forged_witnesses(self):
        good = example(3)
        for bad in ("", good + "\n" + good,
                    good.replace("write_x=16", "write_x=0"),
                    good.replace("first_after_x=17", "first_after_x=50"),
                    good.replace("next_line_samples=16", "next_line_samples=15"),
                    good.replace("shifted_samples=64", "shifted_samples=63"),
                    good.replace("new_fine=3", "new_fine=2"),
                    good.replace("original_game_midframe_scroll_proven=no",
                                 "original_game_midframe_scroll_proven=yes")):
            with self.subTest(sample=bad[:40]), self.assertRaises(DynamicScrollError):
                verify_report(bad, 3)
        with self.assertRaises(DynamicScrollError):
            verify_report(good, 3, xbuf={"switch_source_scanline": 105})

    def test_reject_phase_missing_duplicate_or_wrong_row(self):
        samples = [(v, verify_report(example(v), v)) for v in VALUES]
        with self.assertRaises(DynamicScrollError):
            verify_sweep(samples[:-1])
        duplicate = [samples[0], samples[0], samples[2], samples[3]]
        with self.assertRaises(DynamicScrollError):
            verify_sweep(duplicate)
        wrong = [(phase, dict(data)) for phase, data in samples]
        wrong[1][1]["write_source_scanline"] = 105
        with self.assertRaises(DynamicScrollError):
            verify_sweep(wrong)


@unittest.skipUnless(shutil.which("c++"), "C++ compiler absent")
class NativeHeader(unittest.TestCase):
    def test_actual_cpp11_scroll_write_and_pixels_with_negative_control(self):
        source = """#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main(int argc,char**argv) {
 unsigned fine=argc>1?static_cast<unsigned>(argv[1][0]-'0'):3;
 setenv("VPD_STAGE117_DYNAMIC_SCROLL_PROBE","1",1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 char expected[2]={static_cast<char>('0'+fine),0};
 setenv("VPD_STAGE117_EXPECT_FINE",expected,1);
 vpd_ppu_probe::stage110_register_write(2,0);
 for(unsigned sl=1;sl<=110;++sl) {
  for(unsigned x=0;x<256;++x) {
   if(sl==104 && x==16) {
    vpd_ppu_probe::stage110_register_write(2,1);
    vpd_ppu_probe::stage117_scroll_write(fine,0);
   }
   unsigned bank=sl>=105 ? 255U : (sl==104 && x>=48 ? 255U : 0U);
   unsigned curfine=(sl>104 || (sl==104 && x>=16))?fine:0;
   unsigned tile=(x+curfine)>>3, bgpx=(x+curfine)&7;
   vpd_ppu_probe::stage117_pixel(sl,x/8,x%8,tile,bgpx,curfine,
                                  bank,bank,bank?3U:0U);
   vpd_ppu_probe::stage110_raster_pixel(sl,bank?3U:0U,bank?48U:15U);
   ++vpd_ppu_probe::channel().internal_tick_units;
  }
 }
 return 0;
}"""
        with tempfile.TemporaryDirectory() as tmp:
            cpp, exe = Path(tmp)/"case.cpp", Path(tmp)/"case"
            flags = ["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                     "-pedantic", "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                     "-DVPD_NATIVE_SYNTHETIC_DYNAMIC_SCROLL", "-I",
                     str(ROOT / "tools"), str(cpp), "-o", str(exe)]
            cpp.write_text(source)
            built = subprocess.run(flags, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            for target in VALUES:
                result = subprocess.run([str(exe), str(target)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(verify_report(result.stderr, target)[
                    "write_source_scanline"], 104)
            cpp.write_text(source.replace(
                "tile,bgpx,curfine,", "tile,bgpx,0,"))
            built = subprocess.run(flags, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            bad = subprocess.run([str(exe), "3"], capture_output=True, text=True)
            self.assertEqual(bad.returncode, 0, bad.stderr)
            self.assertNotIn("VPD_STAGE117_NATIVE_DYNAMIC_SCROLL_PASS", bad.stderr)
            self.assertIn("VPD_STAGE117_REJECTED_DYNAMIC_SCROLL", bad.stderr)


if __name__ == "__main__":
    unittest.main()
