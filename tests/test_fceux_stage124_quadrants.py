"""Stage124 native four-quadrant PPU output and synthetic ROM controls."""
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_stage123_quadrant_palette import ATTRIBUTE_BYTE, PALETTE_RAM
from make_stage124_native_quadrant_rom import (
    make_rom, initialization, TILE_PAGE, ATTR_LOOP_SUFFIX, PAGE_HIGHS,
)
from run_stage124_native_quadrants import (
    verify, QuadrantNativeError, MARKER, REJECTED,
)
from inject_fceux_stage119_nametable_pixels import patch as stage119_patch
from inject_fceux_stage121_attributes import patch as stage121_patch
from inject_fceux_stage124_quadrants import patch as stage124_patch, GUARD
from test_fceux_stage121_attributes import STAGE118_SOURCE

PASS = (
    "VPD_STAGE124_NATIVE_QUADRANTS_PASS groups=4 "
    "samples=16,16,16,16 indices=3,7,11,15 "
    "xbuf_colors=176,177,178,179 raw_attribute=E4 invalid=0 "
    "actual_fceux_xbuf=yes synthetic_only=yes "
    "original_game_palette_proven=no"
)


class ROM(unittest.TestCase):
    def test_exact_6502_attribute_and_palette_init(self):
        sequence = initialization()
        self.assertEqual(sequence.count(TILE_PAGE), 16)
        self.assertEqual(TILE_PAGE[-2:], bytes((0xD0, 0xFA)))
        self.assertEqual(ATTR_LOOP_SUFFIX[-2:], bytes((0xD0, 0xF8)))
        self.assertEqual(sequence.count(ATTR_LOOP_SUFFIX), 4)
        for page in PAGE_HIGHS:
            start = bytes((0xA9, page, 0x8D, 6, 0x20,
                           0xA9, 0xC0, 0x8D, 6, 0x20))
            self.assertEqual(sequence.count(start), 1)
        for palette in PALETTE_RAM:
            self.assertIn(bytes((0xA9, palette, 0x8D, 7, 0x20)), sequence)

    def test_rom_variant_integrity_and_strict_arguments(self):
        with tempfile.TemporaryDirectory() as folder:
            a, b, c, d = [Path(folder)/(k+".nes") for k in "abcd"]
            hashes = (
                make_rom(a), make_rom(b, attribute=0),
                make_rom(c, distinct_palette=False),
                make_rom(d, switch=False),
            )
            self.assertEqual(len(set(hashes)), 4)
            images = [p.read_bytes() for p in (a, b, c, d)]
            for data in images:
                self.assertEqual(data[:16], b"NES\x1a\x02\x02\x40" + bytes(9))
                self.assertEqual(len(data), 49168)
            # Attribute and palette controls modify PRG, not CHR.
            self.assertEqual(images[0][-16384:], images[1][-16384:])
            self.assertEqual(images[0][-16384:], images[2][-16384:])
            self.assertEqual(images[0][-16384:], images[3][-16384:])
            self.assertEqual(images[0][-16384+1024+16:-16384+1024+32],
                             bytes((0xFF,))*16)
            self.assertEqual(sum(1 for x in images[0][-16384:] if x), 16)
            for kwargs in (
                {"attribute": -1}, {"attribute": 256},
                {"attribute": "E4"}, {"attribute": True},
                {"distinct_palette": 1}, {"switch": 0},
            ):
                with self.subTest(args=kwargs), self.assertRaises(ValueError):
                    make_rom(Path(folder)/"bad.nes", **kwargs)


class Hook(unittest.TestCase):
    def test_guarded_exact_post_xbuf_observer(self):
        previous = stage121_patch(stage119_patch(STAGE118_SOURCE))
        patched = stage124_patch(previous)
        self.assertEqual(patched.count(GUARD), 1)
        self.assertEqual(patched.count(b"vpd_ppu_probe::stage124_pixel("), 1)
        self.assertIn(b"bgdata.main[bgtile].vpd_stage121_atraw", patched)
        self.assertIn(b"pixelcolor, *ptr);", patched)
        self.assertEqual(patched.count(b"\r\n"), patched.count(b"\n"))
        with self.assertRaises(ValueError):
            stage124_patch(patched)

    def test_missing_provenance_refused(self):
        good = stage121_patch(stage119_patch(STAGE118_SOURCE))
        for broken in (
            good + good,
            good.replace(b"vpd_ppu_probe::stage121_pixel(", b"removed("),
            good.replace(b"vpd_stage121_ataddr = RefreshAddr", b"missing"),
            good.replace(b"vpd_stage119_ntaddr = NTRefreshAddr", b"missing"),
            good.replace(b"pixel & 3, *ptr);", b"pixel & 3, 0);"),
        ):
            with self.subTest(data=broken[:40]), self.assertRaises(ValueError):
                stage124_patch(broken)
        with self.assertRaises(TypeError):
            stage124_patch(good.decode("ascii"))


class Witness(unittest.TestCase):
    def test_accept_exact_one_native_marker(self):
        self.assertEqual(verify(PASS)["xbuf_colors"], [176, 177, 178, 179])
        self.assertFalse(verify(PASS)["original_game_palette_proven"])

    def test_reject_missing_mutated_duplicated_or_false_proof(self):
        for bad in (
            "", PASS+"\n"+PASS, PASS+"\n"+REJECTED+" invalid=1",
            PASS.replace("176,177,178,179", "176,176,178,179"),
            PASS.replace("176,177,178,179", "177,176,178,179"),
            PASS.replace("samples=16,16,16,16", "samples=15,16,16,16"),
            PASS.replace("raw_attribute=E4", "raw_attribute=00"),
            PASS.replace("actual_fceux_xbuf=yes", "actual_fceux_xbuf=no"),
            PASS.replace("original_game_palette_proven=no",
                         "original_game_palette_proven=yes"),
        ):
            with self.subTest(report=bad[-85:]), self.assertRaises(QuadrantNativeError):
                verify(bad)


@unittest.skipUnless(shutil.which("c++"), "Native C++ compiler not available")
class Native(unittest.TestCase):
    def test_four_group_actual_xbuf_witness_and_rejections(self):
        fixture = r"""
#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main(int argc,char**) {
 setenv("VPD_STAGE124_QUADRANT_PROBE","1",1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 vpd_ppu_probe::stage110_register_write(2,0);
 for(unsigned sl=1;sl<=190;++sl) {
  for(unsigned x=0;x<256;++x) {
   if(sl==104&&x==36) vpd_ppu_probe::stage110_register_write(2,1);
   const unsigned nt=0x2000U+(((sl/8U)%30U)<<5)+(x/8U);
   const unsigned quad=((nt&0x40U)?2U:0U)+((nt&2U)?1U:0U);
   const unsigned ataddr=0x23C0U+(nt&0x0C00U)+
             ((nt&0x0380U)>>4)+((nt&0x001CU)>>2);
   const unsigned index=quad*4U+3U;
   const unsigned color=(argc>2)?0x30U:(0x30U+quad);
   vpd_ppu_probe::stage124_pixel(
       sl,x/8U,x%8U,nt,ataddr,argc>1?0U:0xE4U,
       2U*quad,4U*quad,3U,index,color,0x80U|color);
   vpd_ppu_probe::stage110_raster_pixel(
       sl,sl<105?0U:3U,0x80U|color);
   ++vpd_ppu_probe::channel().internal_tick_units;
  }
 }
 return 0;
}
"""
        with tempfile.TemporaryDirectory() as folder:
            src, exe = Path(folder)/"quad.cpp", Path(folder)/"quad"
            src.write_text(fixture)
            cc = subprocess.run([
                "c++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                "-pedantic", "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                "-DVPD_NATIVE_SYNTHETIC_QUADRANT_COLORS",
                "-I", str(ROOT/"tools"), str(src), "-o", str(exe),
            ], text=True, capture_output=True)
            self.assertEqual(cc.returncode, 0, cc.stderr)
            positive = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(positive.returncode, 0, positive.stderr)
            self.assertIn(MARKER, positive.stderr)
            verify(positive.stderr)
            for args in (["attr"], ["attr", "collision"]):
                control = subprocess.run([str(exe)] + args,
                                         capture_output=True, text=True)
                self.assertEqual(control.returncode, 0, control.stderr)
                self.assertNotIn(MARKER, control.stderr)
                self.assertIn(REJECTED, control.stderr)


if __name__ == "__main__":
    unittest.main()
