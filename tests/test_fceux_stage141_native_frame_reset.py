"""Stage141 true native FCEUX two-frame status-reset and OAM/XBuf regressions."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))

from run_stage141_native_frame_reset import (
    MODES,PASS,REJECT,FrameResetError,verify,verify_rejection,verify_sweep)
from inject_fceux_stage141_frame_reset import (
    patch as patch141,GUARD)
from inject_fceux_stage119_nametable_pixels import patch as patch119
from inject_fceux_stage121_attributes import patch as patch121
from inject_fceux_stage124_quadrants import patch as patch124
from inject_fceux_stage129_sprite_compositor import patch as patch129
from inject_fceux_stage131_dual_sprite import patch as patch131
from inject_fceux_stage133_sprite_flips import patch as patch133
from inject_fceux_stage135_sprite_8x16 import patch as patch135
from inject_fceux_stage137_nine_oam import patch as patch137
from inject_fceux_stage139_temporal_nine import patch as patch139
from test_fceux_stage121_attributes import STAGE118_SOURCE


def positive(mode):
    bit="yes" if mode=="nine_overflow" else "no"
    color=143 if mode=="nine_overflow" else 170
    return ("VPD_STAGE141_NATIVE_FRAME_RESET_PASS "
        "case=%s first_overflow=%s reset_before=%s reset_after=no "
        "second_overflow=%s first_xbuf=%d second_xbuf=%d "
        "samples=16 invalid=0 actual_ppu_reset_and_xbuf=yes "
        "synthetic_only=yes original_game_frame_reset_proven=no"%
        (mode,bit,bit,bit,color,color))


class NativeEvidence(unittest.TestCase):
    def test_both_real_two_frame_certificates_and_total_pixels(self):
        reports=[(mode,verify(positive(mode),mode)) for mode in MODES]
        self.assertEqual(verify_sweep(reports)["samples"],32)
        self.assertEqual(reports[1][1]["before_reset"],"yes")
        self.assertEqual(reports[1][1]["after_reset"],"no")

    def test_forged_or_contradictory_frame_reset_certificates_rejected(self):
        for mode in MODES:
            correct=positive(mode)
            for bad in ("",correct+"\n"+correct,correct+"\n"+REJECT,
                correct.replace("samples=16","samples=8"),
                correct.replace("invalid=0","invalid=1"),
                correct.replace("reset_after=no","reset_after=yes"),
                correct.replace("first_xbuf=","first_xbuf=0"),
                correct.replace("reset_before=","reset_before=forged"),
                correct.replace("actual_ppu_reset_and_xbuf=yes",
                                "actual_ppu_reset_and_xbuf=no"),
                correct.replace("original_game_frame_reset_proven=no",
                                "original_game_frame_reset_proven=yes")):
                with self.subTest(mode=mode,bad=bad[-70:]):
                    with self.assertRaises(FrameResetError):
                        verify(bad,mode)
            wrong=MODES[1-MODES.index(mode)]
            with self.assertRaises(FrameResetError):
                verify(correct,wrong)

    def test_false_eight_sprite_negative_requires_native_overflow(self):
        wrong=("VPD_STAGE141_REJECTED_FRAME_RESET "
            "case=eight_visible invalid=18 first_overflow=yes "
            "reset_before=yes reset_after=no second_overflow=yes "
            "first_xbuf=143 second_xbuf=143 samples=16 synthetic_only=yes")
        self.assertTrue(verify_rejection(wrong)["false_no_overflow"])
        for malformed in ("",wrong+"\n"+wrong,
            wrong.replace("invalid=18","invalid=0"),
            wrong.replace("first_overflow=yes","first_overflow=no"),
            wrong.replace("reset_after=no","reset_after=yes"),
            wrong.replace("second_xbuf=143","second_xbuf=170"),
            wrong.replace("invalid=18","invalid=018"),
            wrong+"\n"+positive("eight_visible")):
            with self.subTest(bad=malformed[-60:]),self.assertRaises(FrameResetError):
                verify_rejection(malformed)


class SourceHook(unittest.TestCase):
    def test_pinned_reset_and_real_evaluation_raster_hooks(self):
        data=patch124(patch121(patch119(STAGE118_SOURCE)))
        data+=(b"\r\nbool havepixel = false;"
               b"\r\nspixel |= (oam[5] & 1) << 1;"
               b"\r\nhavepixel = true;"
               b"\r\n*ptr = PaletteAdjustPixel(pixelcolor);"
               b"\r\noam[5] = CALL_PPUREAD(RefreshAddr);"
               b"\r\npatternAddress += line & 7;"
               b"\r\noamcounts[scanslot] = oamcount;"
               b"\r\nPPU_status = 0;")
        chained=patch139(patch137(patch135(patch133(patch131(patch129(data))))))
        result=patch141(chained)
        self.assertEqual(result.count(GUARD),4)
        for name in (b"stage141_before_reset(",b"stage141_after_reset(",
                     b"stage141_eval(",b"stage141_pixel("):
            self.assertEqual(result.count(name),1)
        self.assertIn(b"SPRAM[32],SPRAM[35]",result)
        self.assertIn(b"vpd_ppu_probe::stage141_after_reset(PPU_status);",result)
        self.assertEqual(result.count(b"\r\n"),result.count(b"\n"))
        with self.assertRaises(ValueError):
            patch141(result)
        for anchor in (b"PPU_status = 0;",
                       b"*ptr = PaletteAdjustPixel(pixelcolor);",
                       b"oamcounts[scanslot] = oamcount;"):
            with self.subTest(anchor=anchor),self.assertRaises(ValueError):
                patch141(chained.replace(anchor,b"missing"))
        with self.assertRaises(TypeError):
            patch141(chained.decode("latin1"))


@unittest.skipUnless(shutil.which("c++"),"C++ compiler not installed")
class CompiledObserver(unittest.TestCase):
    def test_real_header_links_and_tracks_two_frames_through_reset(self):
        code=r"""
#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main(int argc,char**argv){
 if(argc<2)return 3;
 const unsigned mode=(unsigned)std::atoi(argv[1]);
 if(mode>1)return 4;
 const bool false_clean=argc>2;
 const bool overflow=mode==1 || false_clean;
 setenv("VPD_STAGE141_FRAME_RESET_CASE",
        mode==1?"nine_overflow":"eight_visible",1);
 setenv("VPD_STAGE141_FRAME_RESET_PROBE","1",1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 vpd_ppu_probe::stage110_register_write(2,0);
 vpd_ppu_probe::stage110_register_write(2,1);
 for(unsigned frame=0;frame<2;++frame){
  const unsigned status=overflow?0x20U:0U;
  vpd_ppu_probe::stage141_eval(124,8,status,
      overflow?120:255,overflow?64:255,0,1,2,3,4,5,6,7);
  for(unsigned x=64;x<72;++x){
   vpd_ppu_probe::stage141_pixel(126,x,8,status,
      overflow?143:170,false);
  }
  if(frame==0){
   vpd_ppu_probe::stage141_before_reset(status);
   vpd_ppu_probe::stage141_after_reset(0);
  }
 }
 return 0;
}
"""
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"observer.cpp"; binary=Path(td)/"observer"
            src.write_text(code)
            build=subprocess.run(["c++","-std=c++11","-pedantic","-Wall",
                "-Wextra","-Werror","-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                "-DVPD_NATIVE_SYNTHETIC_OVERFLOW_FRAME_RESET",
                "-I",str(ROOT/"tools"),str(src),"-o",str(binary)],
                capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            for i,mode in enumerate(MODES):
                p=subprocess.run([str(binary),str(i)],capture_output=True,text=True)
                self.assertEqual(p.returncode,0,p.stderr)
                verify(p.stderr,mode)
            neg=subprocess.run([str(binary),"0","wrong"],
                               capture_output=True,text=True)
            self.assertEqual(neg.returncode,0,neg.stderr)
            verify_rejection(neg.stderr)


if __name__=="__main__":
    unittest.main()
