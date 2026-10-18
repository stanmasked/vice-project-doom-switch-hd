"""Stage139 two native scanline OAM transitions, final XBuf and controls."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))

from make_stage138_temporal_oam_rom import MODES,expected
from run_stage139_native_temporal_nine import (
    verify,verify_rejection,verify_sweep,TemporalNativeError,PASS,REJECT)
from inject_fceux_stage139_temporal_nine import patch as patch139,GUARD
from inject_fceux_stage119_nametable_pixels import patch as patch119
from inject_fceux_stage121_attributes import patch as patch121
from inject_fceux_stage124_quadrants import patch as patch124
from inject_fceux_stage129_sprite_compositor import patch as patch129
from inject_fceux_stage131_dual_sprite import patch as patch131
from inject_fceux_stage133_sprite_flips import patch as patch133
from inject_fceux_stage135_sprite_8x16 import patch as patch135
from inject_fceux_stage137_nine_oam import patch as patch137
from test_fceux_stage121_attributes import STAGE118_SOURCE


def certificate(mode):
    e=expected(mode)
    a=e["upper"];b=e["lower"]
    return ("VPD_STAGE139_NATIVE_TEMPORAL_NINE_PASS "
        "case=%s top_source=124 bottom_source=132 "
        "top_sl=126 bottom_sl=134 top_count=%d bottom_count=%d "
        "top_overflow=%s bottom_overflow=%s "
        "top_xbuf=%d bottom_xbuf=%d samples=16 invalid=0 "
        "native_fceux_xbuf=yes synthetic_only=yes "
        "original_game_temporal_oam_proven=no" %
        (mode,a["selected_count"],b["selected_count"],
         "yes" if a["sprite_overflow_bit"] else "no",
         "yes" if b["sprite_overflow_bit"] else "no",
         e["xbuf_upper"],e["xbuf_lower"]))


class NativeEvidence(unittest.TestCase):
    def test_four_scenarios_and_64_samples(self):
        reports=[(mode,verify(certificate(mode),mode)) for mode in MODES]
        self.assertEqual(verify_sweep(reports)["samples"],64)
        self.assertEqual(reports[2][1]["bottom_xbuf"],170)

    def test_forged_partial_noncanonical_or_contradicted_witness_rejected(self):
        for mode in MODES:
            valid=certificate(mode)
            changes=("",
                valid+"\n"+valid,valid+"\n"+REJECT,
                valid.replace("samples=16","samples=8"),
                valid.replace("invalid=0","invalid=2"),
                valid.replace("top_source=124","top_source=123"),
                valid.replace("bottom_sl=134","bottom_sl=133"),
                valid.replace("top_count=","top_count=0"),
                valid.replace("bottom_xbuf=","bottom_xbuf=0"),
                valid.replace("native_fceux_xbuf=yes","native_fceux_xbuf=no"),
                valid.replace("original_game_temporal_oam_proven=no",
                              "original_game_temporal_oam_proven=yes"))
            for wrong in changes:
                with self.subTest(mode=mode,corrupt=wrong[-55:]):
                    with self.assertRaises(TemporalNativeError):
                        verify(wrong,mode)
            with self.assertRaises(TemporalNativeError):
                verify(valid,MODES[(MODES.index(mode)+1)%4])

    def test_free_slot_rejection_is_specific(self):
        invalid=("VPD_STAGE139_REJECTED_TEMPORAL_NINE "
                "case=nine_late invalid=16 top_count=7 bottom_count=8 "
                "top_overflow=no bottom_overflow=no "
                "top_xbuf=143 bottom_xbuf=170 "
                "top_sl=126 bottom_sl=134 samples=16 synthetic_only=yes")
        self.assertTrue(verify_rejection(invalid)["rejected"])
        for wrong in ("",invalid+"\n"+invalid,
                      invalid.replace("invalid=16","invalid=0"),
                      invalid.replace("top_count=7","top_count=8"),
                      invalid.replace("bottom_overflow=no","bottom_overflow=yes"),
                      invalid.replace("bottom_xbuf=170","bottom_xbuf=143"),
                      invalid.replace("top_sl=126","top_sl=0126"),
                      invalid+"\n"+certificate("nine_late")):
            with self.subTest(wrong=wrong[-55:]),self.assertRaises(TemporalNativeError):
                verify_rejection(wrong)


class HookSource(unittest.TestCase):
    def test_instrument_real_ppu_once_and_reject_modified_source(self):
        data=patch124(patch121(patch119(STAGE118_SOURCE)))
        data+=(b"\r\nbool havepixel = false;"
               b"\r\nspixel |= (oam[5] & 1) << 1;"
               b"\r\nhavepixel = true;"
               b"\r\n*ptr = PaletteAdjustPixel(pixelcolor);"
               b"\r\noam[5] = CALL_PPUREAD(RefreshAddr);"
               b"\r\npatternAddress += line & 7;"
               b"\r\noamcounts[scanslot] = oamcount;")
        prior=patch137(patch135(patch133(patch131(patch129(data)))))
        patched=patch139(prior)
        self.assertEqual(patched.count(GUARD),2)
        self.assertEqual(patched.count(b"vpd_ppu_probe::stage139_eval("),1)
        self.assertEqual(patched.count(b"vpd_ppu_probe::stage139_pixel("),1)
        self.assertIn(b"yp==124 || yp==132",patched)
        self.assertIn(b"oamcounts[renderslot]",patched)
        self.assertEqual(patched.count(b"\r\n"),patched.count(b"\n"))
        with self.assertRaises(ValueError):
            patch139(patched)
        for anchor in (b"*ptr = PaletteAdjustPixel(pixelcolor);",
                       b"oamcounts[scanslot] = oamcount;"):
            with self.subTest(anchor=anchor),self.assertRaises(ValueError):
                patch139(prior.replace(anchor,b"removed"))
        with self.assertRaises(TypeError):
            patch139(prior.decode("latin1"))


@unittest.skipUnless(shutil.which("c++"),"C++ compiler unavailable")
class NativeCppHeader(unittest.TestCase):
    def test_compiled_two_row_pixel_and_false_nine_control(self):
        code=r"""
#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main(int argc,char**argv) {
 if(argc<2)return 3;
 unsigned mode=(unsigned)std::atoi(argv[1]);
 if(mode>3)return 4;
 bool forged=argc>2;
 const char* labels[]={"eight_stable","nine_late","seven_plus_late","nine_early"};
 setenv("VPD_STAGE139_TEMPORAL_CASE",labels[mode],1);
 setenv("VPD_STAGE139_TEMPORAL_PROBE","1",1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 vpd_ppu_probe::stage110_register_write(2,0);
 for(unsigned sl=1;sl<=140;++sl) {
  for(unsigned x=0;x<256;++x) {
   if(sl==104 && x==36)vpd_ppu_probe::stage110_register_write(2,1);
   if((sl==126||sl==134) && x==64) {
    const bool bottom=sl==134;
    const unsigned count=(mode==2 || forged) && !bottom?7U:8U;
    const unsigned status=(mode==3 || (mode==1 && bottom && !forged))?32U:0U;
    vpd_ppu_probe::stage139_eval(sl-2,count,status,
       0,1,2,3,4,5,6,(mode==2 || forged) && bottom?8:7);
   }
   if((sl==126||sl==134)&&x>=64&&x<72) {
    const bool bottom=sl==134;
    const unsigned count=(mode==2 || forged) && !bottom?7U:8U;
    const unsigned status=(mode==3 || (mode==1 && bottom && !forged))?32U:0U;
    const unsigned color=((mode==2 || forged)&&bottom)?170U:143U;
    vpd_ppu_probe::stage139_pixel(sl,x,count,status,color,true);
   }
   vpd_ppu_probe::stage110_raster_pixel(sl,3U,0xB0U);
   ++vpd_ppu_probe::channel().internal_tick_units;
  }
 }
 return 0;
}
"""
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/"test.cpp"
            exe=Path(td)/"test"
            f.write_text(code)
            cc=subprocess.run(["c++","-std=c++11","-pedantic","-Wall",
                "-Wextra","-Werror",
                "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                "-DVPD_NATIVE_SYNTHETIC_TEMPORAL_NINE",
                "-I",str(ROOT/"tools"),str(f),"-o",str(exe)],
                capture_output=True,text=True)
            self.assertEqual(cc.returncode,0,cc.stderr)
            for i,mode in enumerate(MODES):
                p=subprocess.run([str(exe),str(i)],
                                 capture_output=True,text=True)
                self.assertEqual(p.returncode,0,p.stderr)
                verify(p.stderr,mode)
            negative=subprocess.run([str(exe),"1","forged"],
                                    capture_output=True,text=True)
            self.assertEqual(negative.returncode,0,negative.stderr)
            verify_rejection(negative.stderr)


if __name__=="__main__":
    unittest.main()
