"""Stage150 source and native-certificate regression, no original ROM assets.

Only native pinned FCEUX CI may validate real pre/post PPU/XBuf behavior.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))

from inject_fceux_stage150_dynamic_oam_frames import (
    patch,GUARD,EVAL,DRAW,INCLUDE)
from run_stage150_native_dynamic_oam import (
    PASS,REJECT,DynamicOamError,verify,verify_wrong_case)

SOURCE=(
    b'#include "vpd_stage149_cpu_oam_probe.h"\n'
    b'vpd_ppu_probe::stage149_oam_data(\n'
    b'vpd_ppu_probe::stage141_eval(\n'
    b'vpd_ppu_probe::stage141_pixel(\n'
    b'oamcounts[scanslot] = oamcount;\n'
    b'*ptr = PaletteAdjustPixel(pixelcolor);\n')


def cpu(mode,negative=False):
    active=mode=="activate_ninth" or negative
    v=(160,120,2,0,64,0) if active else (64,255,255,255,255,227)
    return (
        "VPD_STAGE149_NATIVE_VBLANK_OAM_WRITE_%s "
        "case=%s status_high_read=yes oamaddr=31 writes=5 "
        "first_oam=31 last_oam=35 oam7_x=%d oam8_y=%d "
        "oam8_tile=%d oam8_attr=%d oam8_x=%d attr_stored=%d "
        "invalid=%d synthetic_only=yes original_game_oam_writes_proven=no"
        % ("REJECT" if negative else "PASS",mode,*v,5 if negative else 0))


def frame(mode,negative=False):
    active=mode=="activate_ninth" or negative
    return (
        "VPD_STAGE150_NATIVE_OAM_FRAME_%s case=%s "
        "before_count=8 after_count=8 before_overflow=no "
        "after_overflow=%s before_xbuf=170 after_xbuf=%d "
        "before_raw=42 after_raw=%d before_sprite=1 "
        "after_sprite=%d oam7_before=64 oam7_after=%d "
        "oam8_y_before=255 oam8_y_after=%d "
        "cpu_writes=5 samples=16 invalid=%d "
        "synthetic_only=yes original_game_dynamic_oam_proven=no"
        % ("REJECT" if negative else "PASS",mode,
           "yes" if active else "no",143 if active else 170,
           15 if active else 42,0 if active else 1,
           160 if active else 64,120 if active else 255,
           8 if negative else 0))


class PinnedSourceHook(unittest.TestCase):
    def test_guarded_renderer_hooks_are_both_real_sites(self):
        for source in (SOURCE,SOURCE.replace(b"\n",b"\r\n")):
            with self.subTest(crlf=b"\r\n" in source):
                result=patch(source)
                self.assertEqual(result.count(GUARD),3)
                self.assertEqual(result.count(b"stage150_eval("),1)
                self.assertEqual(result.count(b"stage150_pixel("),1)
                self.assertIn(b"SPRAM[31],SPRAM[32],SPRAM[35]",result)
                self.assertIn(b"oams[scanslot][7][6]",result)
                self.assertIn(b"pixelcolor,havepixel,pixel & 3",result)
                if b"\r\n" in source:
                    self.assertEqual(result.count(b"\r\n"),result.count(b"\n"))
                with self.assertRaises(ValueError):patch(result)

    def test_source_mutations_are_refused(self):
        for needle in (INCLUDE,EVAL,DRAW,
                       b"vpd_ppu_probe::stage149_oam_data(",
                       b"vpd_ppu_probe::stage141_eval(",
                       b"vpd_ppu_probe::stage141_pixel("):
            with self.subTest(anchor=needle),self.assertRaises(ValueError):
                patch(SOURCE.replace(needle,b"altered"))
        with self.assertRaises(TypeError):patch(SOURCE.decode("ascii"))


class NativeCerts(unittest.TestCase):
    def test_both_frame_proofs_require_matching_real_cpu_writes(self):
        for mode in ("activate_ninth","preserve_eight"):
            log=cpu(mode)+"\n"+frame(mode)
            with self.subTest(mode=mode):
                record=verify(log,mode)
                self.assertEqual(record["samples"],16)
                self.assertEqual(record["before_xbuf"],170)
                self.assertEqual(record["after_xbuf"],
                                 143 if mode=="activate_ninth" else 170)
                self.assertTrue(record["observed_native_dynamic_oam"])

    def test_wrong_mode_requires_real_cpu_and_ppu_rejections(self):
        bad=cpu("preserve_eight",True)+"\n"+frame("preserve_eight",True)
        self.assertTrue(verify_wrong_case(bad)["rejected"])
        for altered in ("",frame("preserve_eight",True),
                        cpu("preserve_eight",True),
                        bad.replace("invalid=8","invalid=0"),
                        bad.replace("invalid=5","invalid=4")):
            with self.subTest(value=altered[-65:]):
                with self.assertRaises(DynamicOamError):
                    verify_wrong_case(altered)

    def test_missing_duplicate_noncanonical_and_forged_positive_fails(self):
        for mode in ("activate_ninth","preserve_eight"):
            base=cpu(mode)+"\n"+frame(mode)
            for i,log in enumerate((
                "",frame(mode),cpu(mode),
                base+"\n"+frame(mode),base+"\n"+cpu(mode),
                base+"\n"+REJECT,
                base.replace("samples=16","samples=8"),
                base.replace("before_count=8","before_count=7"),
                base.replace("before_xbuf=170","before_xbuf=171"),
                base.replace("after_raw=","after_raw=0"),
                base.replace("after_sprite=","after_sprite=2"),
                base.replace("after_overflow=","after_overflow=forged"),
                base.replace("cpu_writes=5","cpu_writes=04"),
                base.replace("original_game_dynamic_oam_proven=no",
                             "original_game_dynamic_oam_proven=yes"),
                base.replace("original_game_oam_writes_proven=no",
                             "original_game_oam_writes_proven=yes"),
            )):
                with self.subTest(mode=mode,mutation=i):
                    with self.assertRaises(DynamicOamError):
                        verify(log,mode)


@unittest.skipUnless(shutil.which("c++"),"C++ compiler unavailable")
class CompiledObserver(unittest.TestCase):
    def test_cpp_oam_to_xbuf_causality_and_corrupt_post_pixel(self):
        source=r'''
#include "vpd_newppu_raw_step_probe.h"
#include "vpd_stage149_cpu_oam_probe.h"
#include "vpd_stage150_dynamic_oam_frame_probe.h"
#include <cstdlib>
int main(int argc,char**argv){
 if(argc<3)return 3;
 const bool activated=argv[1][0]=='a';
 const bool bad=argv[2][0]=='b';
 setenv("VPD_STAGE149_OAM_WRITES_PROBE","1",1);
 setenv("VPD_STAGE149_OAM_WRITES_CASE",
        activated?"activate_ninth":"preserve_eight",1);
 setenv("VPD_STAGE150_DYNAMIC_OAM_PROBE","1",1);
 setenv("VPD_STAGE150_DYNAMIC_OAM_CASE",
        activated?"activate_ninth":"preserve_eight",1);
 const unsigned ids[8]={0,1,2,3,4,5,6,7};
 vpd_ppu_probe::stage150_eval(124,8,0,64,255,255,
    ids[0],ids[1],ids[2],ids[3],
    ids[4],ids[5],ids[6],ids[7]);
 for(unsigned x=64;x<72;x++){
  vpd_ppu_probe::stage150_pixel(126,x,8,0,170,false,42,true,0);
 }
 vpd_ppu_probe::Stage149OamAudit& cpu=vpd_ppu_probe::stage149_oam_state();
 cpu.writes=5;cpu.high_reads=1;cpu.addr_writes=1;cpu.emitted=true;
 const unsigned status=activated?32:0;
 const unsigned out=activated?143:170;
 const unsigned raw=activated?15:42;
 vpd_ppu_probe::stage150_eval(124,8,status,
     activated?160:64,activated?120:255,activated?64:255,
     ids[0],ids[1],ids[2],ids[3],
     ids[4],ids[5],ids[6],ids[7]);
 for(unsigned x=64;x<72;x++){
  vpd_ppu_probe::stage150_pixel(126,x,8,status,
      (bad && x==71)?out+1:out,false,
      raw,!activated,0);
 }
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"probe.cpp"; exe=Path(td)/"probe"
            src.write_text(source)
            build=subprocess.run([
                "c++","-std=c++11","-Wall","-Wextra","-Werror",
                "-pedantic","-DVPD_NATIVE_SYNTHETIC_OAM_CPU_WRITES",
                "-DVPD_NATIVE_SYNTHETIC_DYNAMIC_OAM_FRAMES",
                "-I",str(ROOT/"tools"),str(src),"-o",str(exe)],
                capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            for mode,tag in (("activate_ninth","a"),("preserve_eight","p")):
                for fault in ("ok","bad"):
                    with self.subTest(mode=mode,fault=fault):
                        run=subprocess.run([str(exe),tag,fault],
                                           capture_output=True,text=True)
                        self.assertEqual(run.returncode,0,run.stderr)
                        self.assertIn(
                            REJECT if fault=="bad" else PASS,run.stderr)
                        self.assertNotIn(
                            PASS if fault=="bad" else REJECT,run.stderr)


if __name__=="__main__":
    unittest.main()
