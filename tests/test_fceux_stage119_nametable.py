"""Stage119 nametable-read identity and real XBuf source proof regressions."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from make_stage119_nametable_rom import make_rom, nametable_init
from inject_fceux_stage119_nametable_pixels import (
    patch, PIXEL, WRITE,
)
from run_stage119_native_nametable import (
    FINES, TileIdentityError, verify_report, verify_sweep,
)

SOURCE = (
    b"vpd_ppu_probe::stage115_edge_read(sl, xt, bgdata.main[xt].pt[0], "
    b"bgdata.main[xt].pt[1]);\r\n" +
    WRITE + b"\r\n" + PIXEL + b"\r\n"
)
PASS = (
    "VPD_STAGE119_NATIVE_NAMETABLE_PASS fine1={fine} fine2={second} "
    "coarse1=0 coarse2=1 write_sl1=104 write_sl2=105 "
    "sample_sl1=105 sample_sl2=106 "
    "nametable0_x0=0 nametable1_x0=1 "
    "pattern0_x0=0 pattern1_x0=3 "
    "first_color=15 second_color=48 samples_per_row=16 "
    "odd_first=7 odd_second=9 invalid=0 "
    "real_fceux_xbuf=yes synthetic_only=yes "
    "original_game_coarse_scroll_proven=no"
)


class ROM(unittest.TestCase):
    def test_6502_nametable_loop_and_nes_dimensions(self):
        init = nametable_init()
        self.assertEqual(init.count(bytes((0xa2, 0, 0x8a, 0x29, 1,
                                          0x8d, 7, 0x20, 0xe8, 0xd0, 0xf7))), 4)
        with tempfile.TemporaryDirectory() as tmp:
            for fine in FINES:
                path = Path(tmp) / ("%d.nes" % fine)
                make_rom(path, first=fine)
                data = path.read_bytes()
                self.assertEqual(len(data), 49168)
                self.assertEqual(data[:16], b"NES\x1a\x02\x02\x40" + bytes(9))
                self.assertIn(init, data[:16384])
                chr_bank1 = data[-16384+1024:-16384+2048]
                self.assertEqual(chr_bank1[0:16], bytes(16))
                self.assertEqual(chr_bank1[16:32], bytes((255,))*16)
                self.assertEqual(chr_bank1[32:48], bytes(16))

    def test_changing_only_chromatic_tile_proof_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/"d.nes", Path(tmp)/"u.nes"
            make_rom(a, first=3)
            make_rom(b, first=3, differentiated=False)
            d, u = a.read_bytes(), b.read_bytes()
            self.assertEqual(d[:-16384], u[:-16384])
            self.assertNotEqual(d[-16384:], u[-16384:])
            self.assertEqual(u[-16384:], bytes(16384))

    def test_reject_invalid_input_without_silent_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/"bad.nes"
            for v in (-1, 0, 2, 4, 9, 3.0, True, "3"):
                with self.subTest(v=v), self.assertRaises(ValueError):
                    make_rom(p, first=v)
            for key in ("differentiated", "switch"):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    make_rom(p, **{key: 1})


class Hook(unittest.TestCase):
    def test_pinned_register_and_buffered_nt_to_xbuf(self):
        out = patch(SOURCE)
        self.assertEqual(out.count(b"stage119_write("), 1)
        self.assertEqual(out.count(b"stage119_pixel("), 1)
        self.assertIn(b"bgdata.main[bgtile].nt", out)
        self.assertIn(b"pixel & 3, *ptr", out)
        self.assertEqual(out.count(b"\r\n"), out.count(b"\n"))

    def test_double_patch_missing_or_duplicate_provenance_rejected(self):
        for source in (SOURCE+SOURCE, patch(SOURCE),
                       SOURCE.replace(PIXEL, b"none"),
                       SOURCE.replace(WRITE, b"none"),
                       SOURCE.replace(b"stage115_edge_read", b"lost")):
            with self.subTest(source=source[:25]), self.assertRaises(ValueError):
                patch(source)


class Witness(unittest.TestCase):
    def test_accept_all_four_mock_native_records(self):
        records = []
        for fine in FINES:
            result = verify_report(PASS.format(fine=fine, second=8-fine), fine)
            self.assertFalse(result["original_game_coarse_scroll_proven"])
            records.append((fine, result))
        self.assertEqual(verify_sweep(records)["first_sl"], 104)

    def test_reject_mismatched_color_tile_origin_or_unjustified_claim(self):
        good = PASS.format(fine=3, second=5)
        for bad in ("", good+"\n"+good,
                    good.replace("second_color=48", "second_color=15"),
                    good.replace("nametable1_x0=1", "nametable1_x0=0"),
                    good.replace("pattern1_x0=3", "pattern1_x0=0"),
                    good.replace("sample_sl2=106", "sample_sl2=107"),
                    good.replace("coarse2=1", "coarse2=0"),
                    good.replace("invalid=0", "invalid=1"),
                    good.replace("original_game_coarse_scroll_proven=no",
                                 "original_game_coarse_scroll_proven=yes")):
            with self.subTest(line=bad[:42]), self.assertRaises(TileIdentityError):
                verify_report(bad, 3)
        with self.assertRaises(TileIdentityError):
            verify_sweep([(fine, verify_report(
                PASS.format(fine=fine, second=8-fine), fine))
                          for fine in FINES[:-1]])


@unittest.skipUnless(shutil.which("c++"), "Native C++ compiler unavailable")
class Native(unittest.TestCase):
    def test_cpp11_real_header_distinguishable_nt_and_negative_corruption(self):
        fixture = """#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main(int argc, char** argv) {
 unsigned fine=argc>1?static_cast<unsigned>(argv[1][0]-'0'):3;
 char expected[]={static_cast<char>('0'+fine),0};
 setenv("VPD_STAGE119_NAMETABLE_PROBE","1",1);
 setenv("VPD_STAGE119_FIRST_FINE",expected,1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 vpd_ppu_probe::stage110_register_write(2,0);
 // Boot-time $2005 X=0 is not a visible midframe scroll event.
 vpd_ppu_probe::stage119_write(0,0);
 for(unsigned sl=1;sl<=107;++sl) {
  for(unsigned x=0;x<256;++x) {
   if(sl==104 && x==36) vpd_ppu_probe::stage110_register_write(2,1);
   if(sl==104 && x==39) vpd_ppu_probe::stage119_write(fine,0);
   if(sl==105 && x==151) vpd_ppu_probe::stage119_write(8-fine,1);
   const unsigned scroll=sl>=106||(sl==105&&x>=151) ?
       8-fine : (sl>=105||(sl==104&&x>=39)?fine:0U);
   const unsigned bgtile=(x+scroll)>>3, bgpx=(x+scroll)&7;
   const unsigned source=(bgtile+(sl>=106?1U:0U))&1U;
   const unsigned n=source, plane=source?255U:0U;
   const unsigned pixel=source?3U:0U;
   vpd_ppu_probe::stage119_pixel(sl,x/8,x%8,bgtile,bgpx,
      scroll,sl>=106?1U:0U,n,plane,plane,pixel,source?48U:15U);
   vpd_ppu_probe::stage110_raster_pixel(sl,sl<105?0U:pixel,
                                         source?48U:15U);
   ++vpd_ppu_probe::channel().internal_tick_units;
  }
 }
 return 0;
}"""
        with tempfile.TemporaryDirectory() as tmp:
            cpp, exe = Path(tmp)/"nt.cpp", Path(tmp)/"nt"
            args = ["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                    "-pedantic", "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                    "-DVPD_NATIVE_SYNTHETIC_NAMETABLE_IDS",
                    "-I", str(ROOT/"tools"), str(cpp), "-o", str(exe)]
            cpp.write_text(fixture)
            p = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            for fine in FINES:
                r = subprocess.run([str(exe), str(fine)],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn("VPD_STAGE119_NATIVE_NAMETABLE_PASS", r.stderr)
            cpp.write_text(fixture.replace(
                "const unsigned n=source, plane=source?255U:0U;",
                "const unsigned n=0, plane=source?255U:0U;"))
            p = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            r = subprocess.run([str(exe), "3"], capture_output=True, text=True)
            self.assertNotIn("VPD_STAGE119_NATIVE_NAMETABLE_PASS", r.stderr)
            self.assertIn("VPD_STAGE119_REJECTED_NAMETABLE", r.stderr)


if __name__ == "__main__":
    unittest.main()
