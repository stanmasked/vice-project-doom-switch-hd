"""Stage131 paired OAM ROM integrity, native C++ observation and strict reports."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from make_stage131_dual_sprite_rom import (
    MODES,make_rom,dual_oam_init,SPRITE_PALETTE0_COLOR,
    SPRITE_PALETTE1_COLOR,
)
from run_stage131_native_dual_sprite import (
    expectations,verify,verify_rejection,verify_sweep,DualSpriteError,
    MARKER,REJECTED,
)
from inject_fceux_stage119_nametable_pixels import patch as patch119
from inject_fceux_stage121_attributes import patch as patch121
from inject_fceux_stage124_quadrants import patch as patch124
from inject_fceux_stage129_sprite_compositor import patch as patch129
from inject_fceux_stage131_dual_sprite import patch as patch131, GUARD
from test_fceux_stage121_attributes import STAGE118_SOURCE


def report(mode,q=0,row=124):
    e=expectations(mode,q)
    return ("VPD_STAGE131_NATIVE_DUAL_SPRITES_PASS "
            "case=%s row=%d quadrant=%d sample_x=64 samples=8 "
            "oam_count=2 first_pattern=%d second_pattern=%d "
            "claimed_oam=%d sprite0_hit=%s xbuf=%d invalid=0 "
            "actual_fceux_dual_oam_xbuf=yes synthetic_only=yes "
            "original_game_sprites_proven=no" %
            (mode,row,q,e["first_pattern"],e["second_pattern"],
             e["claimed_oam"],"yes" if e["sprite0_hit"] else "no",e["xbuf"]))


class ROM(unittest.TestCase):
    def test_two_oam_entries_distinct_palettes_and_byte_differences(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            values={}
            for mode in MODES:
                p=root/(mode+".nes")
                make_rom(p,mode)
                values[mode]=p.read_bytes()
            for data in values.values():
                self.assertEqual(len(data),49168)
                self.assertEqual(data[:16],b"NES\x1a\x02\x02\x40"+bytes(9))
                self.assertEqual(data[-16384+1024+32:-16384+1024+48],b"\xff"*16)
                self.assertEqual(data[-16384+1024+48:-16384+1024+64],bytes(16))
            a=values["first_front"]
            for mode,count in (("palette_swapped",8),("first_transparent",4),
                               ("first_behind",4),("first_behind_clear",20)):
                with self.subTest(mode=mode):
                    differences=[i for i,(u,v) in enumerate(zip(a,values[mode]))
                                 if u!=v]
                    self.assertEqual(len(differences),count)
            self.assertEqual(a[-16384:],values["palette_swapped"][-16384:])
            self.assertEqual(a[-16384:],values["first_transparent"][-16384:])
            self.assertNotEqual(a[-16384:],values["first_behind_clear"][-16384:])
            bad=root/"transparent_second.nes"
            make_rom(bad,"first_transparent",second_opaque=False)
            neg=bad.read_bytes()
            self.assertEqual(neg[-16384:],values["first_transparent"][-16384:])
            self.assertEqual(sum(u!=v for u,v in zip(neg,values["first_transparent"])),4)

    def test_oam_sequence_and_invalid_controls_fail_closed(self):
        init=dual_oam_init("first_front")
        self.assertEqual(init.count(bytes((0xa9,120,0x8d,4,0x20))),2)
        self.assertEqual(init.count(bytes((0xa9,64,0x8d,4,0x20))),2)
        self.assertIn(bytes((0xa9,SPRITE_PALETTE0_COLOR,0x8d,7,0x20)),init)
        self.assertIn(bytes((0xa9,SPRITE_PALETTE1_COLOR,0x8d,7,0x20)),init)
        with tempfile.TemporaryDirectory() as td:
            bad=Path(td)/"bad.nes"
            for mode,second in (("wrong",True),("first_front",1),
                                ("first_front",None),("first_front","yes")):
                with self.subTest(mode=mode,second=second):
                    with self.assertRaises(ValueError):
                        make_rom(bad,mode,second_opaque=second)
                    self.assertFalse(bad.exists())


class Hook(unittest.TestCase):
    def test_four_guarded_exact_source_sites_and_duplicate_reject(self):
        ready=patch124(patch121(patch119(STAGE118_SOURCE)))
        ready+=(b"\r\nbool havepixel = false;"
                b"\r\nspixel |= (oam[5] & 1) << 1;"
                b"\r\nhavepixel = true;"
                b"\r\n*ptr = PaletteAdjustPixel(pixelcolor);")
        parent=patch129(ready)
        new=patch131(parent)
        self.assertEqual(new.count(GUARD),4)
        self.assertEqual(new.count(b"vpd_ppu_probe::stage131_pixel("),1)
        self.assertIn(b"vpd131_claim=s;",new)
        self.assertIn(b"oams[renderslot][1][2]",new)
        self.assertEqual(new.count(b"\r\n"),new.count(b"\n"))
        with self.assertRaises(ValueError):
            patch131(new)
        for anchor in (b"bool havepixel = false;",
                       b"havepixel = true;",
                       b"spixel |= (oam[5] & 1) << 1;"):
            with self.subTest(anchor=anchor):
                with self.assertRaises(ValueError):
                    patch131(parent.replace(anchor,b"missing"))
        with self.assertRaises(TypeError):
            patch131(parent.decode("latin1"))


class Report(unittest.TestCase):
    def test_five_reports_and_native_negative(self):
        records=[(mode,verify(report(mode),mode)) for mode in MODES]
        self.assertEqual(verify_sweep(records)["pixel_samples"],40)
        negative=("VPD_STAGE131_REJECTED_DUAL_SPRITES "
                  "case=first_transparent invalid=8 "
                  "row=124 quadrant=0 xbuf=176 samples=8 synthetic_only=yes")
        self.assertTrue(verify_rejection(negative,"first_transparent")["rejected"])
        for bad in ("",negative+"\n"+negative,negative+"\n"+report("first_transparent"),
                    negative.replace("invalid=8","invalid=0"),
                    negative.replace("xbuf=176","xbuf=184")):
            with self.subTest(bad=bad[-50:]),self.assertRaises(DualSpriteError):
                verify_rejection(bad,"first_transparent")

    def test_forged_and_swapped_reports_refused(self):
        for mode in MODES:
            good=report(mode)
            for bad in ("",good+"\n"+good,
                        good+"\nVPD_STAGE131_REJECTED_DUAL_SPRITES",
                        good.replace("invalid=0","invalid=1"),
                        good.replace("samples=8","samples=7"),
                        good.replace("claimed_oam=","claimed_oam=9"),
                        good.replace("sprite0_hit=","sprite0_hit=wrong-"),
                        good.replace("actual_fceux_dual_oam_xbuf=yes",
                                     "actual_fceux_dual_oam_xbuf=no"),
                        good.replace("original_game_sprites_proven=no",
                                     "original_game_sprites_proven=yes")):
                with self.subTest(mode=mode,bad=bad[-50:]),self.assertRaises(DualSpriteError):
                    verify(bad,mode)
            wrong=MODES[(MODES.index(mode)+1)%len(MODES)]
            with self.assertRaises(DualSpriteError):
                verify(good,wrong)


@unittest.skipUnless(shutil.which("c++"),"C++11 compiler unavailable")
class NativeCpp(unittest.TestCase):
    def test_compiled_header_five_modes_and_both_zero_negative(self):
        code=r"""
#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main(int argc,char**argv) {
 if(argc<2)return 2;
 const unsigned mode=(unsigned)atoi(argv[1]);
 if(mode>4)return 2;
 static const char* cases[]={"first_front","palette_swapped",
     "first_transparent","first_behind","first_behind_clear"};
 setenv("VPD_STAGE131_DUAL_PROBE","1",1);
 setenv("VPD_STAGE131_DUAL_CASE",cases[mode],1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 vpd_ppu_probe::stage110_register_write(2,0);
 for(unsigned sl=1;sl<=130;++sl) {
  for(unsigned x=0;x<256;++x) {
   if(sl==104&&x==36)vpd_ppu_probe::stage110_register_write(2,1);
   if(sl==124&&x>=64&&x<72) {
    const bool wrong=argc>2;
    const unsigned first=(mode==2)?0U:3U;
    const unsigned second=wrong?0U:3U;
    const int claim=wrong?-1:((mode==2)?1:0);
    const unsigned bg=(mode==4)?0U:3U;
    const unsigned color=wrong?0x30U:
          ((mode==1||mode==2)?0x38U:((mode==3)?0x30U:0x2AU));
    const unsigned hit=(mode==2||mode==4||wrong)?0U:0x40U;
    const unsigned attr0=(mode==1)?1U:(mode>=3)?0x20U:0U;
    const unsigned attr1=(mode==1)?0U:1U;
    vpd_ppu_probe::stage131_pixel(
      sl,x,2,120U,(mode==2)?3U:2U,attr0,64U,
      120U,wrong?3U:2U,attr1,64U,
      true,first,true,second,claim,bg,color,hit,0x80U|color,0x2088U);
   }
   vpd_ppu_probe::stage110_raster_pixel(sl,3U,0xB0U);
   ++vpd_ppu_probe::channel().internal_tick_units;
  }
 }
 return 0;
}
"""
        with tempfile.TemporaryDirectory() as td:
            src,exe=Path(td)/"dual.cpp",Path(td)/"dual"
            src.write_text(code)
            cc=subprocess.run(["c++","-std=c++11","-Wall","-Wextra","-Werror",
                "-pedantic","-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                "-DVPD_NATIVE_SYNTHETIC_DUAL_SPRITE",
                "-I",str(ROOT/"tools"),str(src),"-o",str(exe)],
                capture_output=True,text=True)
            self.assertEqual(cc.returncode,0,cc.stderr)
            for i,mode in enumerate(MODES):
                proc=subprocess.run([str(exe),str(i)],capture_output=True,text=True)
                self.assertEqual(proc.returncode,0,proc.stderr)
                verify(proc.stderr,mode)
            negative=subprocess.run([str(exe),"2","zero_second"],
                                    capture_output=True,text=True)
            self.assertEqual(negative.returncode,0,negative.stderr)
            self.assertIn(REJECTED,negative.stderr)
            self.assertNotIn(MARKER,negative.stderr)


if __name__=="__main__":
    unittest.main()
