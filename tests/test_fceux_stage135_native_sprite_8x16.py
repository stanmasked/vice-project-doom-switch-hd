"""Stage135: fail-closed 8x16 source hooks, native XBuf certificate and C++ probe."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from make_stage134_sprite_8x16_rom import MODES,make_rom
from run_stage135_native_sprite_8x16 import (
    Native16Error,verify,verify_rejection,verify_sweep,PASS,REJECT,expected
)
from inject_fceux_stage119_nametable_pixels import patch as patch119
from inject_fceux_stage121_attributes import patch as patch121
from inject_fceux_stage124_quadrants import patch as patch124
from inject_fceux_stage129_sprite_compositor import patch as patch129
from inject_fceux_stage131_dual_sprite import patch as patch131
from inject_fceux_stage133_sprite_flips import patch as patch133
from inject_fceux_stage135_sprite_8x16 import patch as patch135,GUARD
from test_fceux_stage121_attributes import STAGE118_SOURCE


def sample(mode):
    flip=mode.endswith("vertical")
    sl_top,sl_bottom=(132,124) if flip else (124,132)
    top,bottom=expected(mode)
    return ("VPD_STAGE135_NATIVE_8X16_PASS "
        "mode=%s top_row=4 bottom_row=12 top_sl=%d bottom_sl=%d "
        "top_xbuf=%d bottom_xbuf=%d samples=16 invalid=0 "
        "actual_fceux_8x16_xbuf=yes synthetic_only=yes "
        "original_game_8x16_proven=no" %
        (mode,sl_top,sl_bottom,top,bottom))


class NativeCertificate(unittest.TestCase):
    def test_four_cases_and_scanline_pairing(self):
        results=[(m,verify(sample(m),m)) for m in MODES]
        self.assertEqual(verify_sweep(results)["samples"],64)
        self.assertEqual(results[0][1]["upper_xbuf"],154)
        self.assertEqual(results[2][1]["upper_xbuf"],171)

    def test_inconsistent_or_forged_reports_fail_closed(self):
        for mode in MODES:
            good=sample(mode)
            for corrupt in (
                "",good+"\n"+good,good+"\n"+REJECT,
                good.replace("samples=16","samples=8"),
                good.replace("invalid=0","invalid=1"),
                good.replace("top_row=4","top_row=17"),
                good.replace("top_xbuf=","top_xbuf=0"),
                good.replace("actual_fceux_8x16_xbuf=yes",
                             "actual_fceux_8x16_xbuf=no"),
                good.replace("original_game_8x16_proven=no",
                             "original_game_8x16_proven=yes")):
                with self.subTest(mode=mode,corrupt=corrupt[-70:]):
                    with self.assertRaises(Native16Error):
                        verify(corrupt,mode)
            different=MODES[(MODES.index(mode)+1)%4]
            with self.assertRaises(Native16Error):
                verify(good,different)

    def test_rejected_wrong_bank_must_be_native_and_specific(self):
        control=("VPD_STAGE135_REJECTED_8X16 "
            "mode=even_normal invalid=16 ordering_bad=no "
            "top_row=4 bottom_row=12 top_sl=124 bottom_sl=132 "
            "top_xbuf=154 bottom_xbuf=170 samples=16 synthetic_only=yes")
        self.assertTrue(verify_rejection(control)["wrong_bank"])
        for wrong in ("",control+"\n"+control,
                      control+"\n"+sample("even_normal"),
                      control.replace("invalid=16","invalid=0"),
                      control.replace("mode=even_normal","mode=odd_normal"),
                      control.replace("top_xbuf=154","top_xbuf=171"),
                      control.replace("ordering_bad=no","ordering_bad=yes")):
            with self.subTest(wrong=wrong[-60:]),self.assertRaises(Native16Error):
                verify_rejection(wrong)


class GuardedHook(unittest.TestCase):
    def test_exact_real_ppu_anchor_and_no_double_patch(self):
        source=patch124(patch121(patch119(STAGE118_SOURCE)))
        source+=(b"\r\nbool havepixel = false;"
                 b"\r\nspixel |= (oam[5] & 1) << 1;"
                 b"\r\nhavepixel = true;"
                 b"\r\n*ptr = PaletteAdjustPixel(pixelcolor);"
                 b"\r\noam[5] = CALL_PPUREAD(RefreshAddr);"
                 b"\r\npatternAddress += line & 7;")
        parent=patch133(patch131(patch129(source)))
        instrument=patch135(parent)
        self.assertEqual(instrument.count(GUARD),2)
        self.assertEqual(instrument.count(b"vpd_ppu_probe::stage135_fetch("),1)
        self.assertEqual(instrument.count(b"vpd_ppu_probe::stage135_pixel("),1)
        self.assertIn(b"oam[7] && (oam[1]==2 || oam[1]==3)",instrument)
        self.assertEqual(instrument.count(b"\r\n"),instrument.count(b"\n"))
        with self.assertRaises(ValueError):
            patch135(instrument)
        for anchor in (b"*ptr = PaletteAdjustPixel(pixelcolor);",
                       b"oam[5] = CALL_PPUREAD(RefreshAddr);",
                       b"patternAddress += line & 7;"):
            with self.subTest(anchor=anchor),self.assertRaises(ValueError):
                patch135(parent.replace(anchor,b"missing"))
        with self.assertRaises(TypeError):
            patch135(parent.decode("latin1"))


@unittest.skipUnless(shutil.which("c++"),"C++ compiler unavailable")
class CppNativeObserver(unittest.TestCase):
    def test_real_header_compiles_both_sprite_halves_and_negative(self):
        code=r"""
#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main(int argc,char**argv){
 if(argc<2)return 3;
 const unsigned mode=(unsigned)atoi(argv[1]);
 if(mode>3)return 4;
 const bool wrong=argc>2;
 const bool odd=mode<2,flip=(mode%2)!=0;
 const unsigned tile=(odd||wrong)?3U:2U;
 const unsigned flags=flip?0x80U:0U;
 const char* names[]={"odd_normal","odd_vertical","even_normal","even_vertical"};
 setenv("VPD_STAGE135_8X16_PROBE","1",1);
 setenv("VPD_STAGE135_8X16_MODE",names[mode],1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 vpd_ppu_probe::stage110_register_write(2,0);
 for(unsigned sl=1;sl<=138;++sl){
  for(unsigned x=0;x<256;++x){
   if(sl==104&&x==36)vpd_ppu_probe::stage110_register_write(2,1);
   if((sl==124||sl==132)&&x==64){
    const bool lower=flip?(sl==124):(sl==132);
    const unsigned row=lower?12U:4U;
    const unsigned pat=odd?(lower?3U:1U):(lower?1U:2U);
    const unsigned addr=(odd?4096U:0U)+32U+(lower?16U:0U)+4U;
    vpd_ppu_probe::stage135_fetch(0,0,row,addr,
      (pat&1U)?255U:0U,(pat&2U)?255U:0U,flags,tile,true);
   }
   if((sl==124||sl==132)&&x>=64&&x<72){
    const bool lower=flip?(sl==124):(sl==132);
    const unsigned pat=odd?(lower?3U:1U):(lower?1U:2U);
    const unsigned color=(pat==1)?0x1AU:(pat==2)?0x2BU:0x2AU;
    vpd_ppu_probe::stage135_pixel(sl,x,0,tile,flags,64U,true,pat,
                                  color,0x80U|color);
   }
   vpd_ppu_probe::stage110_raster_pixel(sl,3U,0xB0U);
   ++vpd_ppu_probe::channel().internal_tick_units;
  }
 }
 return 0;
}
"""
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/"stage135.cpp"
            out=Path(td)/"stage135"
            f.write_text(code)
            cc=subprocess.run([
                "c++","-std=c++11","-Wall","-Wextra","-Werror","-pedantic",
                "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                "-DVPD_NATIVE_SYNTHETIC_SPRITE_8X16",
                "-I",str(ROOT/"tools"),str(f),"-o",str(out)
            ],capture_output=True,text=True)
            self.assertEqual(cc.returncode,0,cc.stderr)
            for i,mode in enumerate(MODES):
                p=subprocess.run([str(out),str(i)],capture_output=True,text=True)
                self.assertEqual(p.returncode,0,p.stderr)
                verify(p.stderr,mode)
            negative=subprocess.run([str(out),"2","wrongbank"],
                                    capture_output=True,text=True)
            self.assertEqual(negative.returncode,0,negative.stderr)
            self.assertIn(REJECT,negative.stderr)
            self.assertNotIn(PASS,negative.stderr)


if __name__=="__main__":
    unittest.main()
