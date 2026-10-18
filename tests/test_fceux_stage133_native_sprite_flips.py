"""Stage133 native reflected CHR sprite, OAM flags, XBuf and forged reports."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from make_stage129_oam_sprite_rom import make_rom, asymmetric_pattern
from run_stage133_native_sprite_flips import (
    MODES,MARKER,REJECTED,NativeFlipError,flags_for,reference,
    verify,verify_rejection,verify_sweep
)
from inject_fceux_stage119_nametable_pixels import patch as patch119
from inject_fceux_stage121_attributes import patch as patch121
from inject_fceux_stage124_quadrants import patch as patch124
from inject_fceux_stage129_sprite_compositor import patch as patch129
from inject_fceux_stage131_dual_sprite import patch as patch131
from inject_fceux_stage133_sprite_flips import patch as patch133,GUARD
from test_fceux_stage121_attributes import STAGE118_SOURCE


def report(mode,source_row=4,row=124):
    pat,colors=reference(mode,source_row)
    return (
        "VPD_STAGE133_NATIVE_SPRITE_FLIP_PASS "
        "mode=%s row=%d source_row=%d samples=8 "
        "patterns=%s xbuf=%s invalid=0 "
        "actual_fceux_sprite_flips=yes synthetic_only=yes "
        "original_game_flips_proven=no" %
        (mode,row,source_row,",".join(map(str,pat)),
         ",".join(map(str,colors)))
    )


class ROM(unittest.TestCase):
    def test_four_asymmetric_chr_roms_differ_only_flip_immediate(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            originals={}
            for mode in MODES:
                horizontal,vertical=flags_for(mode)
                rom=root/(mode+".nes")
                make_rom(rom,asymmetric_sprite=True,
                         hflip=horizontal,vflip=vertical)
                originals[mode]=rom.read_bytes()
            for data in originals.values():
                self.assertEqual(data[:16],b"NES\x1a\x02\x02\x40"+bytes(9))
                self.assertEqual(len(data),49168)
            base=originals["none"]
            for mode in MODES[1:]:
                other=originals[mode]
                changed=[i for i,(a,b) in enumerate(zip(base,other)) if a!=b]
                self.assertEqual(len(changed),4)
                self.assertEqual(len({(i-16)%8192 for i in changed}),1)
                self.assertEqual(other[-16384:],base[-16384:])
                self.assertEqual({base[i] for i in changed},{0})
                self.assertEqual({other[i] for i in changed},
                                 {0x40*(mode in ("horizontal","both"))+
                                  0x80*(mode in ("vertical","both"))})
            for row in range(8):
                low=base[-16384+1024+32+row]
                high=base[-16384+1024+40+row]
                for col in range(8):
                    pixel=((low>>(7-col))&1)|(((high>>(7-col))&1)<<1)
                    self.assertEqual(pixel,asymmetric_pattern(row,col))
                    self.assertIn(pixel,(1,2,3))
            opaque=root/"legacy.nes"
            make_rom(opaque)
            old=opaque.read_bytes()
            self.assertEqual(old[:32784],base[:32784])
            self.assertNotEqual(old[-16384:],base[-16384:])

    def test_invalid_flip_flags_and_chr_coordinates_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/"bad.nes"
            for bad in (None,1,"yes",0):
                with self.subTest(flag=bad):
                    with self.assertRaises(ValueError):
                        make_rom(output,hflip=bad,asymmetric_sprite=True)
                    self.assertFalse(output.exists())
        for row,column in ((-1,0),(8,0),(0,8),(0,-1),(True,0)):
            with self.assertRaises(ValueError):
                asymmetric_pattern(row,column)


class Injection(unittest.TestCase):
    def test_exact_dual_ppu_anchor_guard_and_replay_refusal(self):
        source=patch124(patch121(patch119(STAGE118_SOURCE)))
        source+=(b"\r\nbool havepixel = false;"
                 b"\r\nspixel |= (oam[5] & 1) << 1;"
                 b"\r\nhavepixel = true;"
                 b"\r\n*ptr = PaletteAdjustPixel(pixelcolor);"
                 b"\r\noam[5] = CALL_PPUREAD(RefreshAddr);")
        stage131=patch131(patch129(source))
        stage133=patch133(stage131)
        self.assertEqual(stage133.count(GUARD),2)
        self.assertEqual(stage133.count(b"vpd_ppu_probe::stage133_pixel("),1)
        self.assertEqual(stage133.count(b"vpd_ppu_probe::stage133_fetch("),1)
        self.assertIn(b"vpd_stage129_pattern",stage133)
        # FCEUX fills unused evaluation slots with dummy tile0 CHR reads.
        # The fetch witness must accept only a genuine OAM0 tile2,
        # rather than allowing a later dummy read to overwrite it.
        self.assertIn(
            b"if(s==0 && oam[7] && oam[1]==2 && oam[6]==0)",
            stage133)
        self.assertIn(b"vpd_ppu_probe::stage133_fetch(",stage133)

        self.assertEqual(stage133.count(b"\r\n"),stage133.count(b"\n"))
        with self.assertRaises(ValueError):
            patch133(stage133)
        for anchor in (b"oam[5] = CALL_PPUREAD(RefreshAddr);",
                       b"*ptr = PaletteAdjustPixel(pixelcolor);",
                       b"vpd_ppu_probe::stage131_pixel("):
            with self.subTest(anchor=anchor), self.assertRaises(ValueError):
                patch133(stage131.replace(anchor,b"removed"))
        with self.assertRaises(TypeError):
            patch133(stage131.decode("latin1"))


class Evidence(unittest.TestCase):
    def test_all_flips_and_strict_source_row_pairing(self):
        samples=[
            ("none",verify(report("none",4),"none")),
            ("horizontal",verify(report("horizontal",4),"horizontal")),
            ("vertical",verify(report("vertical",3),"vertical")),
            ("both",verify(report("both",3),"both")),
        ]
        result=verify_sweep(samples)
        self.assertEqual(result["samples"],32)
        self.assertTrue(result["native_flip_pixels_proven"])
        self.assertFalse(result["original_game_flips_proven"])

    def test_wrong_source_row_and_forged_reports_rejected(self):
        for mode in MODES:
            good=report(mode)
            for malformed in (
                "",good+"\n"+good,
                good+"\n"+REJECTED+" invalid=1",
                good.replace("source_row=4","source_row=9"),
                good.replace("samples=8","samples=7"),
                good.replace("invalid=0","invalid=1"),
                good.replace("patterns=","patterns=0,"),
                good.replace("xbuf=","xbuf=0,"),
                good.replace("actual_fceux_sprite_flips=yes",
                             "actual_fceux_sprite_flips=no"),
                good.replace("original_game_flips_proven=no",
                             "original_game_flips_proven=yes"),
            ):
                with self.subTest(mode=mode),self.assertRaises(NativeFlipError):
                    verify(malformed,mode)
            with self.assertRaises(NativeFlipError):
                verify(good,MODES[(MODES.index(mode)+1)%4])
        fail=("VPD_STAGE133_REJECTED_SPRITE_FLIP "
              "mode=horizontal invalid=8 row=124 source_row=4 "
              "samples=8 synthetic_only=yes")
        self.assertTrue(verify_rejection(fail)["rejected"])
        for wrong in ("",fail+"\n"+fail,fail+"\n"+report("horizontal"),
                      fail.replace("invalid=8","invalid=0"),
                      fail.replace("mode=horizontal","mode=vertical")):
            with self.assertRaises(NativeFlipError):
                verify_rejection(wrong)


@unittest.skipUnless(shutil.which("c++"),"C++ compiler unavailable")
class NativeCpp(unittest.TestCase):
    def test_header_witness_four_flip_modes_and_corrupted_flag(self):
        code=r"""
#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main(int argc,char** argv) {
 if(argc<2)return 2;
 const unsigned mode=(unsigned)atoi(argv[1]);
 if(mode>3)return 2;
 const char* names[]={"none","horizontal","vertical","both"};
 setenv("VPD_STAGE133_FLIP_MODE",names[mode],1);
 setenv("VPD_STAGE133_FLIP_PROBE","1",1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 vpd_ppu_probe::stage110_register_write(2,0);
 for(unsigned sl=1;sl<=124;++sl) {
  for(unsigned x=0;x<256;++x) {
   if(sl==104&&x==36)vpd_ppu_probe::stage110_register_write(2,1);
   if(sl==124&&x==64) {
    const unsigned row=(mode&2U)?3U:4U;
    unsigned low=0U,high=0U;
    for(unsigned col=0;col<8;++col) {
     const unsigned pat=vpd_ppu_probe::stage133_pattern(row,col);
     low|=(pat&1U)<<(7U-col);
     high|=((pat>>1)&1U)<<(7U-col);
    }
    const unsigned flags=(mode&1U?0x40U:0U)|(mode&2U?0x80U:0U);
    vpd_ppu_probe::stage133_fetch(0,0,row,0x1020U+row,low,high,flags);
   }
   if(sl==124&&x>=64&&x<72) {
    const unsigned row=(mode&2U)?3U:4U;
    const unsigned col=(mode&1U)?(7U-(x-64U)):(x-64U);
    const unsigned pat=vpd_ppu_probe::stage133_pattern(row,col);
    const unsigned color=(pat==1U)?0x1AU:(pat==2U)?0x2BU:0x2AU;
    const unsigned flags=(mode&1U?0x40U:0U)|(mode&2U?0x80U:0U);
    const bool wrongflag=argc>2&&argv[2][0]=='f';
    const bool wrongcolor=argc>2&&argv[2][0]=='c'&&x==67U;
    const unsigned observed_color=wrongcolor?(color^1U):color;
    vpd_ppu_probe::stage133_pixel(
       sl,x,0,2U,wrongflag?flags^0x40U:flags,64U,
       true,pat,observed_color,0x80U|observed_color,0x2088U);
   }
   vpd_ppu_probe::stage110_raster_pixel(sl,3U,0xB0U);
   ++vpd_ppu_probe::channel().internal_tick_units;
  }
 }
 return 0;
}
"""
        with tempfile.TemporaryDirectory() as td:
            source,exe=Path(td)/"stage133.cpp",Path(td)/"stage133"
            source.write_text(code)
            c=subprocess.run(["c++","-std=c++11","-Wall","-Wextra","-Werror",
                "-pedantic","-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                "-DVPD_NATIVE_SYNTHETIC_SPRITE_FLIPS",
                "-I",str(ROOT/"tools"),str(source),"-o",str(exe)],
                text=True,capture_output=True)
            self.assertEqual(c.returncode,0,c.stderr)
            for i,mode in enumerate(MODES):
                proc=subprocess.run([str(exe),str(i)],
                                    text=True,capture_output=True)
                self.assertEqual(proc.returncode,0,proc.stderr)
                verify(proc.stderr,mode)
            bad=subprocess.run([str(exe),"1","flipflag"],
                               text=True,capture_output=True)
            self.assertEqual(bad.returncode,0,bad.stderr)
            self.assertIn(REJECTED,bad.stderr)
            self.assertNotIn(MARKER,bad.stderr)
            color_bad=subprocess.run([str(exe),"0","color"],
                                     text=True,capture_output=True)
            self.assertEqual(color_bad.returncode,0,color_bad.stderr)
            self.assertIn(REJECTED,color_bad.stderr)
            self.assertNotIn(MARKER,color_bad.stderr)
            self.assertIn("VPD_STAGE133_COLOR_DIAGNOSTIC",color_bad.stderr)
            self.assertIn("invalid=1",color_bad.stderr)
            self.assertIn("bad_meta=0 bad_fetch=0 bad_pattern=0 bad_color=1",
                          color_bad.stderr)


if __name__=="__main__":
    unittest.main()
