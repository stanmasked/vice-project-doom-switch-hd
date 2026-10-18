"""Stage129 synthetic sprite OAM/PROM integrity and native observer tests."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from make_stage129_oam_sprite_rom import (
    make_rom,sprite_initialization,SPRITE_Y,SPRITE_X,SPRITE_COLOR
)
from run_stage129_native_sprite_oam import (
    SCENARIOS,MARKER,REJECTED,SpriteNativeError,verify,verify_sweep
)
from inject_fceux_stage119_nametable_pixels import patch as stage119_patch
from inject_fceux_stage121_attributes import patch as stage121_patch
from inject_fceux_stage124_quadrants import patch as stage124_patch
from inject_fceux_stage129_sprite_compositor import patch as stage129_patch,GUARD
from test_fceux_stage121_attributes import STAGE118_SOURCE

def marker(bg=True,sp=True,behind=False,mask=True,q=0,sl=124):
    visible=sp and mask and (not behind or not bg)
    hit=sp and mask and bg
    color=170 if visible else 176+q if bg else 143
    return (
        "VPD_STAGE129_NATIVE_SPRITE_OAM_PASS "
        "bg=%s sprite=%s priority=%s mask=%s "
        "sl=%d sample_x=64 samples=8 quadrant=%d "
        "sprite_pattern=%d bg_pattern=%d "
        "sprite_visible=%s sprite0_hit=%s xbuf=%d invalid=0 "
        "actual_fceux_oam_and_xbuf=yes synthetic_only=yes "
        "original_game_sprite_proven=no" % (
            "opaque" if bg else "transparent",
            "solid" if sp else "transparent",
            "behind" if behind else "front",
            "enabled" if mask else "disabled",
            sl,q,3 if sp else 0,3 if bg else 0,
            "yes" if visible else "no",
            "yes" if hit else "no",color)
    )

class ROM(unittest.TestCase):
    def test_four_primary_variants_only_modify_intended_ppu_data(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            values=[]
            for name,bg,sp,behind,mask in SCENARIOS:
                path=root/(name+".nes")
                make_rom(path,bg_opaque=bg,sprite_opaque=sp,
                         behind=behind,sprite_enabled=mask)
                values.append(path.read_bytes())
            for v in values:
                self.assertEqual(v[:16],b"NES\x1a\x02\x02\x40"+bytes(9))
                self.assertEqual(len(v),49168)
                self.assertEqual(v[-16384+1024+32:-16384+1024+48],
                                 b"\xFF"*16)
                self.assertEqual(v[-16384+1024+48:-16384+1024+64],
                                 b"\x00"*16)
            # Just the OAM priority immediate changes (four repeated PRG banks).
            opaque_front,opaque_behind=values[0:2]
            change=[i for i,(a,b) in enumerate(zip(opaque_front,opaque_behind)) if a!=b]
            self.assertEqual(len(change),4)
            self.assertEqual({(i-16)%8192 for i in change}.__len__(),1)
            self.assertEqual({opaque_front[i] for i in change},{0})
            self.assertEqual({opaque_behind[i] for i in change},{0x20})
            # BG pattern tile1 differs while OAM tile2 is always solid.
            bg_blank=values[2]
            bg_change=[i for i,(a,b) in enumerate(zip(opaque_front,bg_blank)) if a!=b]
            self.assertEqual(len(bg_change),16)
            self.assertTrue(all(i>=32784 for i in bg_change))
            # Transparent sprite changes its selected tile ID, not CHR.
            transparent_sprite=values[4]
            self.assertEqual(transparent_sprite[-16384:],opaque_front[-16384:])
            self.assertEqual(sum(a!=b for a,b in zip(
                transparent_sprite,opaque_front)),4)

    def test_oam_and_palette_source_bytes_and_modes(self):
        oam=sprite_initialization(behind=True,sprite_opaque=False)
        for val in (SPRITE_Y,3,0x20,SPRITE_X):
            self.assertIn(bytes((0xA9,val,0x8D,4,0x20)),oam)
        self.assertIn(bytes((0xA9,SPRITE_COLOR,0x8D,7,0x20)),oam)
        with tempfile.TemporaryDirectory() as td:
            for key in ("bg_opaque","sprite_opaque","behind","sprite_enabled"):
                with self.assertRaises(ValueError):
                    make_rom(Path(td)/"bad.nes",**{key:1})
        with self.assertRaises(ValueError):
            sprite_initialization(behind=1)

class Injection(unittest.TestCase):
    def test_guarded_pinned_real_sprite_hook(self):
        ready=stage124_patch(stage121_patch(stage119_patch(STAGE118_SOURCE)))
        # Stage118's tiny fixture intentionally excludes sprite renderer.
        # Append its exact source anchors, preserving CRLF.
        ready+=(
            b"\r\n\t\t\t\t\t\tbool havepixel = false;"
            b"\r\n\t\t\t\t\t\t\t\tspixel |= (oam[5] & 1) << 1;"
            b"\r\n\t\t\t\t\t\t*ptr = PaletteAdjustPixel(pixelcolor);"
        )
        patch=stage129_patch(ready)
        self.assertEqual(patch.count(GUARD),3)
        self.assertEqual(patch.count(b"vpd_ppu_probe::stage129_pixel("),1)
        self.assertIn(b"if(s==0){vpd_stage129_read=true;",patch)
        self.assertIn(b"pixelcolor, PPU_status, *ptr",patch)
        self.assertEqual(patch.count(b"\r\n"),patch.count(b"\n"))
        with self.assertRaises(ValueError):
            stage129_patch(patch)
        for anchor in (
            b"bool havepixel = false;",
            b"spixel |= (oam[5] & 1) << 1;",
            b"*ptr = PaletteAdjustPixel(pixelcolor);",
        ):
            with self.subTest(anchor=anchor),self.assertRaises(ValueError):
                stage129_patch(ready.replace(anchor,b"removed();"))
        with self.assertRaises(TypeError):
            stage129_patch(ready.decode("latin1"))

class Reports(unittest.TestCase):
    def test_six_positive_case_sweep(self):
        runs=[]
        for name,bg,sp,behind,mask in SCENARIOS:
            result=verify(marker(bg,sp,behind,mask),
                          bg_opaque=bg,sprite_opaque=sp,
                          behind=behind,sprite_enabled=mask)
            runs.append((name,result))
        self.assertEqual(verify_sweep(runs)["pixel_samples"],48)
        self.assertFalse(runs[1][1]["sprite_visible"])
        self.assertTrue(runs[1][1]["sprite0_hit"])
        self.assertTrue(runs[3][1]["sprite_visible"])
        self.assertFalse(runs[3][1]["sprite0_hit"])

    def test_forged_or_wrong_status_rejected(self):
        correct=marker()
        for forged in (
            "",correct+"\n"+correct,correct+"\n"+REJECTED,
            correct.replace("xbuf=170","xbuf=176"),
            correct.replace("sprite0_hit=yes","sprite0_hit=no"),
            correct.replace("sprite_visible=yes","sprite_visible=no"),
            correct.replace("sample_x=64","sample_x=65"),
            correct.replace("samples=8","samples=7"),
            correct.replace("sl=124","sl=99"),
            correct.replace("actual_fceux_oam_and_xbuf=yes",
                            "actual_fceux_oam_and_xbuf=no"),
            correct.replace("original_game_sprite_proven=no",
                            "original_game_sprite_proven=yes"),
        ):
            with self.subTest(report=forged[-80:]),self.assertRaises(SpriteNativeError):
                verify(forged,bg_opaque=True,sprite_opaque=True,
                       behind=False,sprite_enabled=True)
        with self.assertRaises(SpriteNativeError):
            verify(correct,bg_opaque=False,sprite_opaque=True,
                   behind=False,sprite_enabled=True)


@unittest.skipUnless(shutil.which("c++"),"C++ compiler unavailable")
class NativeCpp(unittest.TestCase):
    def test_exact_header_sprite_priority_hit_and_corruption(self):
        code=r"""
#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main(int argc,char**argv){
 if(argc<2)return 3;
 const unsigned mode=(unsigned)atoi(argv[1]);
 setenv("VPD_STAGE129_SPRITE_PROBE","1",1);
 setenv("VPD_STAGE129_BG", (mode==2||mode==3)?"transparent":"opaque",1);
 setenv("VPD_STAGE129_SPRITE", mode==4?"transparent":"solid",1);
 setenv("VPD_STAGE129_PRIORITY",(mode==1||mode==3)?"behind":"front",1);
 setenv("VPD_STAGE129_MASK",mode==5?"disabled":"enabled",1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 vpd_ppu_probe::stage110_register_write(2,0);
 for(unsigned sl=1;sl<=130;++sl){
  for(unsigned x=0;x<256;++x){
   if(sl==104&&x==36)vpd_ppu_probe::stage110_register_write(2,1);
   if(sl==124&&x>=64&&x<72){
    const bool bg=(mode!=2&&mode!=3);
    const bool sp=(mode!=4);
    const bool behind=(mode==1||mode==3);
    const bool mask=(mode!=5);
    const bool have=sp&&mask;
    const bool visible=have&&(!behind||!bg);
    const bool hit=have&&bg;
    unsigned color=visible?0x2AU:(bg?0x30U:0x0FU);
    if(argc>2)color=0x1CU;
    vpd_ppu_probe::stage129_pixel(sl,x,1,120U,sp?2U:3U,
       behind?0x20U:0U,64U,true,sp?3U:0U,have,
       bg?3U:0U,color,hit?0x40U:0U,0x80U|color,0x2088U);
   }
   vpd_ppu_probe::stage110_raster_pixel(sl,3U,0x80U|0x30U);
   ++vpd_ppu_probe::channel().internal_tick_units;
  }
 }
 return 0;
}
"""
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/"stage129.cpp"
            binary=Path(folder)/"stage129"
            source.write_text(code)
            compile_=subprocess.run([
                "c++","-std=c++11","-Wall","-Wextra","-Werror","-pedantic",
                "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                "-DVPD_NATIVE_SYNTHETIC_SPRITE_COLLISION",
                "-I",str(ROOT/"tools"),str(source),"-o",str(binary)
            ],text=True,capture_output=True)
            self.assertEqual(compile_.returncode,0,compile_.stderr)
            for index,(_,bg,sp,behind,mask) in enumerate(SCENARIOS):
                result=subprocess.run([str(binary),str(index)],
                                      capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                verify(result.stderr,bg_opaque=bg,sprite_opaque=sp,
                       behind=behind,sprite_enabled=mask)
            corrupted=subprocess.run([str(binary),"0","bad"],
                                     capture_output=True,text=True)
            self.assertIn(REJECTED,corrupted.stderr)
            self.assertNotIn(MARKER,corrupted.stderr)


if __name__=="__main__":
    unittest.main()
