"""Stage137 nine OAM native source, synthetic ROM, C++ and forged report tests."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))

from make_stage137_nine_sprite_rom import MODES,make_rom,oam_setup,OAM_CLEAR
from run_stage137_native_nine_oam import (
    verify,verify_rejection,verify_sweep,NativeNineError,expectation,PASS,REJECT
)
from inject_fceux_stage137_nine_oam import patch as patch137, GUARD
from inject_fceux_stage119_nametable_pixels import patch as patch119
from inject_fceux_stage121_attributes import patch as patch121
from inject_fceux_stage124_quadrants import patch as patch124
from inject_fceux_stage129_sprite_compositor import patch as patch129
from inject_fceux_stage131_dual_sprite import patch as patch131
from inject_fceux_stage133_sprite_flips import patch as patch133
from inject_fceux_stage135_sprite_8x16 import patch as patch135
from test_fceux_stage121_attributes import STAGE118_SOURCE


def positive(mode):
    bit,col=expectation(mode)
    row=132 if mode=="nine_8x16" else 124
    return ("VPD_STAGE137_NATIVE_NINE_OAM_PASS case=%s "
            "row=%d eval_row=%d count=8 overflow=%s xbuf=%d "
            "samples=8 invalid=0 observed_oam_and_xbuf=yes "
            "synthetic_only=yes original_game_overflow_proven=no"%
            (mode,row,row,bit,col))


class GeneratedROM(unittest.TestCase):
    def test_four_generated_oam_cases_and_unmodified_chr(self):
        with tempfile.TemporaryDirectory() as td:
            images={}
            for mode in MODES:
                p=Path(td)/(mode+".nes")
                make_rom(p,mode)
                images[mode]=p.read_bytes()
            for image in images.values():
                self.assertEqual(image[:16],b"NES\x1a\x02\x02\x40"+bytes(9))
                self.assertEqual(len(image),49168)
            self.assertEqual(len({b[-16384:] for b in images.values()}),1)
            self.assertEqual(images["nine_overflow"][-16384+1024+16:-16384+1024+32],
                             bytes(16))
            self.assertEqual(images["nine_overflow"][-16384+1024+32:-16384+1024+48],
                             bytes((255,))*16)
            self.assertEqual(len(oam_setup("eight_visible")),len(OAM_CLEAR)+8*4*5)
            self.assertEqual(len(oam_setup("nine_overflow")),len(OAM_CLEAR)+9*4*5)
            self.assertEqual(len(OAM_CLEAR),20)
            self.assertEqual(OAM_CLEAR[-11:],bytes((0x8D,4,0x20,0xE8,0xD0,0xFA,0xA9,0,0x8D,3,0x20)))
            for mode in MODES:
                self.assertTrue(oam_setup(mode).startswith(OAM_CLEAR))
            self.assertEqual(oam_setup("nine_overflow")[-5:],
                             bytes((0xA9,64,0x8D,4,0x20)))
            self.assertEqual(oam_setup("ninth_offscreen")[-20:-15],
                             bytes((0xA9,40,0x8D,4,0x20)))
            self.assertEqual(oam_setup("eight_visible")[-5:],
                             bytes((0xA9,64,0x8D,4,0x20)))
            for mode,image in images.items():
                program=image[16:16+8192]
                self.assertIn(oam_setup(mode),program)
                self.assertEqual(image[16:16+8192],image[16+8192:16+2*8192])
                self.assertEqual(image[16:16+8192],image[16+2*8192:16+3*8192])
                self.assertEqual(image[16:16+8192-6],
                                 image[16+3*8192:16+4*8192-6])
                self.assertEqual(image[16+32768-6:16+32768],
                                 b"\x00\xC0"*3)
                # Payload must occur once per bank; vector bytes are fixed.
                self.assertEqual(image[16:16+32768].count(oam_setup(mode)),4)

    def test_unknown_control_fails_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            for mode in ("","many","nine_hack",None,True):
                path=Path(td)/"bad.nes"
                with self.subTest(mode=mode),self.assertRaises(ValueError):
                    make_rom(path,mode)
                self.assertFalse(path.exists())


class SourceHook(unittest.TestCase):
    def test_real_render_and_evaluation_hooks_and_mutations(self):
        source=patch124(patch121(patch119(STAGE118_SOURCE)))
        source+=(b"\r\nbool havepixel = false;"
                 b"\r\nspixel |= (oam[5] & 1) << 1;"
                 b"\r\nhavepixel = true;"
                 b"\r\n*ptr = PaletteAdjustPixel(pixelcolor);"
                 b"\r\noam[5] = CALL_PPUREAD(RefreshAddr);"
                 b"\r\npatternAddress += line & 7;"
                 b"\r\noamcounts[scanslot] = oamcount;")
        parent=patch135(patch133(patch131(patch129(source))))
        out=patch137(parent)
        self.assertEqual(out.count(GUARD),2)
        self.assertIn(b"SPRAM[32],SPRAM[35]",out)
        self.assertIn(b"oamcounts[renderslot]",out)
        self.assertEqual(out.count(b"vpd_ppu_probe::stage137_eval("),1)
        self.assertEqual(out.count(b"vpd_ppu_probe::stage137_pixel("),1)
        with self.assertRaises(ValueError):
            patch137(out)
        for anchor in (b"oamcounts[scanslot] = oamcount;",
                       b"*ptr = PaletteAdjustPixel(pixelcolor);"):
            with self.subTest(anchor=anchor),self.assertRaises(ValueError):
                patch137(parent.replace(anchor,b"removed"))
        with self.assertRaises(TypeError):
            patch137(parent.decode("latin1"))


class Certificate(unittest.TestCase):
    def test_positive_four_modes_and_sweep(self):
        cases=[(mode,verify(positive(mode),mode)) for mode in MODES]
        self.assertEqual(verify_sweep(cases)["samples"],32)

    def test_forged_missing_duplicate_and_wrong_bits(self):
        for mode in MODES:
            good=positive(mode)
            for wrong in ("",good+"\n"+good,good+"\n"+REJECT,
                          good.replace("count=8","count=9"),
                          good.replace("samples=8","samples=7"),
                          good.replace("invalid=0","invalid=1"),
                          good.replace("overflow=","overflow=wrong"),
                          good.replace("xbuf=","xbuf=0"),
                          good.replace("observed_oam_and_xbuf=yes",
                                       "observed_oam_and_xbuf=no"),
                          good.replace("original_game_overflow_proven=no",
                                       "original_game_overflow_proven=yes")):
                with self.subTest(mode=mode),self.assertRaises(NativeNineError):
                    verify(wrong,mode)

    def test_false_eight_control_must_prove_real_overflow(self):
        negative=("VPD_STAGE137_REJECTED_NINE_OAM "
                  "case=eight_visible invalid=8 row=124 eval_row=124 "
                  "count=8 overflow=yes xbuf=143 samples=8 synthetic_only=yes")
        self.assertTrue(verify_rejection(negative)["rejected"])
        for wrong in ("",negative+"\n"+negative,
                      negative.replace("invalid=8","invalid=0"),
                      negative.replace("overflow=yes","overflow=no"),
                      negative.replace("xbuf=143","xbuf=170"),
                      negative.replace("row=124","row=0124"),
                      negative+"\n"+positive("eight_visible")):
            with self.assertRaises(NativeNineError):
                verify_rejection(wrong)


@unittest.skipUnless(shutil.which("c++"),"C++ compiler unavailable")
class MockCppNative(unittest.TestCase):
    def test_all_oam_scenarios_link_header_and_native_reject(self):
        code=r"""
#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main(int argc,char** argv){
 if(argc<2)return 3;
 unsigned mode=(unsigned)atoi(argv[1]);
 if(mode>3)return 4;
 bool wrong=argc>2;
 const char* cases[]={"eight_visible","nine_overflow","ninth_offscreen","nine_8x16"};
 setenv("VPD_STAGE137_NINE_CASE",cases[mode],1);
 setenv("VPD_STAGE137_NINE_PROBE","1",1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 vpd_ppu_probe::stage110_register_write(2,0);
 for(unsigned sl=1;sl<=138;++sl){
  for(unsigned x=0;x<256;++x){
   if(sl==104 && x==36)vpd_ppu_probe::stage110_register_write(2,1);
   if((sl==124 || sl==132)&&x==64){
    const bool real_nine=(mode==1 || mode==3 || wrong);
    const unsigned color=(mode==0 && !wrong)?170U:143U;
    const unsigned status=real_nine?32U:0U;
    unsigned ninth_y=mode==0&&!wrong?255U:mode==2?40U:120U;
    vpd_ppu_probe::stage137_eval(sl,0,8,status,ninth_y,
             mode==0&&!wrong?255U:64U,0,1,2,3,4,5,6,7);
    (void)color;
   }
   if((sl==124 || sl==132)&&x>=64 && x<72){
    const bool nine=mode==1||mode==3||wrong;
    const unsigned status=nine?32U:0U;
    const unsigned color=(mode==0 && !wrong)?170U:143U;
    vpd_ppu_probe::stage137_pixel(sl,x,0,8,status,color,mode==3);
   }
   vpd_ppu_probe::stage110_raster_pixel(sl,3U,0xB0U);
   ++vpd_ppu_probe::channel().internal_tick_units;
  }
 }
 return 0;
}
"""
        with tempfile.TemporaryDirectory() as td:
            src,out=Path(td)/"t.cpp",Path(td)/"t"
            src.write_text(code)
            p=subprocess.run(["c++","-std=c++11","-pedantic","-Wall",
                    "-Wextra","-Werror",
                    "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                    "-DVPD_NATIVE_SYNTHETIC_NINE_OAM",
                    "-I",str(ROOT/"tools"),str(src),"-o",str(out)],
                    capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            for i,mode in enumerate(MODES):
                result=subprocess.run([str(out),str(i)],
                                      capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                verify(result.stderr,mode)
            bad=subprocess.run([str(out),"0","wrong"],
                               capture_output=True,text=True)
            self.assertIn(REJECT,bad.stderr)
            self.assertNotIn(PASS,bad.stderr)


if __name__=="__main__":
    unittest.main()
