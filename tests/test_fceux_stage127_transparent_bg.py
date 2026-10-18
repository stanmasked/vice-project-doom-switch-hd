"""Stage127 blank-background CHR, universal palette and native XBuf proof."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from make_stage124_native_quadrant_rom import make_rom, initialization
from run_stage127_transparent_bg import (
    verify, verify_opaque_rejection, verify_pair, TransparentBGError,
    MARKER, REJECTED,
)


def valid(backdrop):
    xbuf = (128 | backdrop)
    return (
        "VPD_STAGE127_NATIVE_TRANSPARENT_BG_PASS "
        "backdrop=%d samples=16,16,16,16 quadrant_indices=0,4,8,12 "
        "xbuf=%d,%d,%d,%d invalid=0 "
        "actual_fceux_xbuf=yes synthetic_only=yes "
        "original_game_transparency_proven=no" %
        (backdrop, xbuf, xbuf, xbuf, xbuf)
    )


REJECTION = (
    "VPD_STAGE127_REJECTED_TRANSPARENT_BG "
    "backdrop=15 invalid=64 xbuf=176,177,178,179 "
    "samples=16,16,16,16 synthetic_only=yes"
)


class Generator(unittest.TestCase):
    def test_blank_chr_preserves_program_and_palette(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            a, b, c, d = [root / (name + ".nes") for name in "abcd"]
            make_rom(a)
            make_rom(b, transparent_chr=True)
            make_rom(c, transparent_chr=True, backdrop_color=0x1D)
            make_rom(d, transparent_chr=True)
            original, blank, changed, again = [f.read_bytes() for f in (a, b, c, d)]
            self.assertEqual(blank, again)
            self.assertEqual(original[:32784], blank[:32784])
            self.assertEqual(len(blank), 49168)
            self.assertEqual(set(blank[-16384:]), {0})
            self.assertEqual(len([x for x,y in zip(original,blank) if x!=y]),16)
            self.assertEqual(blank[-16384:],changed[-16384:])
            self.assertEqual(blank[:16],changed[:16])
            # Four mirrored universal palette writes; unchanged PRG
            # instructions but one 6502 immediate per 8 KiB bank.
            difference = [i for i,(x,y) in enumerate(zip(blank,changed)) if x!=y]
            self.assertEqual(len(difference),16)
            self.assertEqual(len({(i-16)%8192 for i in difference}),4)
            self.assertEqual({blank[i] for i in difference},{15})
            self.assertEqual({changed[i] for i in difference},{29})
            self.assertEqual(
                initialization(transparent_chr=True, backdrop_color=0x1D).count(
                    bytes((0xA9,0x1D,0x8D,7,0x20))),4)

    def test_reject_unsupported_or_ambiguous_modes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"bad.nes"
            for kwargs in (
                {"transparent_chr": True, "targeted_quadrant": 0},
                {"transparent_chr": True, "backdrop_color": 0},
                {"transparent_chr": True, "backdrop_color": True},
                {"transparent_chr": False, "backdrop_color": 29},
                {"transparent_chr": 1},
            ):
                with self.subTest(arguments=kwargs):
                    with self.assertRaises(ValueError):
                        make_rom(path, **kwargs)
                    self.assertFalse(path.exists())


class StrictAudit(unittest.TestCase):
    def test_two_real_markers_and_explicit_opaque_control(self):
        a = verify(valid(15),15)
        b = verify(valid(29),29)
        n = verify_opaque_rejection(REJECTION)
        self.assertEqual(verify_pair(a,b,n)["samples"],128)
        self.assertEqual(a["xbuf"],[143]*4)
        self.assertEqual(b["xbuf"],[157]*4)

    def test_forged_reports_rejected(self):
        for backdrop in (15,29):
            right=valid(backdrop)
            for bogus in (
                "",right+"\n"+right,right+"\n"+REJECTION,
                right.replace("quadrant_indices=0,4,8,12",
                              "quadrant_indices=0,0,0,0"),
                right.replace("invalid=0","invalid=1"),
                right.replace("samples=16,16,16,16","samples=16,15,16,16"),
                right.replace("actual_fceux_xbuf=yes",
                              "actual_fceux_xbuf=no"),
                right.replace("original_game_transparency_proven=no",
                              "original_game_transparency_proven=yes"),
                right.replace("xbuf="+",".join([str(128|backdrop)]*4),
                              "xbuf=176,177,178,179"),
            ):
                with self.subTest(backdrop=backdrop, report=bogus[-60:]):
                    with self.assertRaises(TransparentBGError):
                        verify(bogus, backdrop)
        for bogus in (
            "",REJECTION+"\n"+REJECTION,REJECTION+"\n"+valid(15),
            REJECTION.replace("invalid=64","invalid=0"),
            REJECTION.replace("176,177,178,179","143,143,143,143"),
            REJECTION.replace("synthetic_only=yes","synthetic_only=no"),
        ):
            with self.subTest(report=bogus[-60:]):
                with self.assertRaises(TransparentBGError):
                    verify_opaque_rejection(bogus)


@unittest.skipUnless(shutil.which("c++"), "Native C++ compiler unavailable")
class NativeCpp(unittest.TestCase):
    def test_native_header_two_backdrops_and_explicit_opaque_rejection(self):
        fixture = r"""
#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main(int argc,char**argv){
 if(argc<2)return 2;
 setenv("VPD_STAGE124_QUADRANT_PROBE","1",1);
 setenv("VPD_STAGE127_BACKDROP",argv[1],1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 const unsigned backdrop=(unsigned)atoi(argv[1]);
 const bool opaque=argc>2;
 vpd_ppu_probe::stage110_register_write(2,0);
 for(unsigned sl=1;sl<=190;++sl) {
  for(unsigned x=0;x<256;++x) {
   if(sl==104&&x==36)vpd_ppu_probe::stage110_register_write(2,1);
   const unsigned nt=0x2000U+(((sl/8U)%30U)<<5)+(x/8U);
   const unsigned q=((nt&0x40U)?2U:0U)+((nt&2U)?1U:0U);
   const unsigned at=0x23C0U+(nt&0x0C00U)+
               ((nt&0x0380U)>>4)+((nt&0x001CU)>>2);
   const unsigned pattern=opaque?3U:0U;
   const unsigned combined=pattern+4U*q;
   const unsigned color=opaque?(0x30U+q):backdrop;
   vpd_ppu_probe::stage124_pixel(
       sl,x/8U,x%8U,nt,at,0xE4U,2U*q,4U*q,
       pattern,combined,color,0x80U|color);
   vpd_ppu_probe::stage110_raster_pixel(
       sl,sl<105?0U:pattern,0x80U|color);
   ++vpd_ppu_probe::channel().internal_tick_units;
  }
 }
 return 0;
}
"""
        with tempfile.TemporaryDirectory() as folder:
            src,exe=Path(folder)/"transparent.cpp",Path(folder)/"transparent"
            src.write_text(fixture)
            compile_=subprocess.run([
                "c++","-std=c++11","-Wall","-Wextra","-Werror","-pedantic",
                "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                "-DVPD_NATIVE_SYNTHETIC_QUADRANT_COLORS",
                "-I",str(ROOT/"tools"),str(src),"-o",str(exe),
            ],capture_output=True,text=True)
            self.assertEqual(compile_.returncode,0,compile_.stderr)
            for backdrop in (15,29):
                result=subprocess.run([str(exe),str(backdrop)],
                                      capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn(MARKER,result.stderr)
                verify(result.stderr,backdrop)
            fail=subprocess.run([str(exe),"15","opaque"],
                                capture_output=True,text=True)
            self.assertEqual(fail.returncode,0,fail.stderr)
            self.assertIn(REJECTED,fail.stderr)
            self.assertTrue(verify_opaque_rejection(fail.stderr)["opaque_rejected"])


if __name__=="__main__":
    unittest.main()
