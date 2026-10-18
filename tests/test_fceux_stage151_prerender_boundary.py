"""Stage151 source-hook and pre-render boundary certificate regressions.

Compiled C++ is a synthetic preflight, not a substitute for native
pinned-FCEUX proof in GitHub Actions.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))

from inject_fceux_stage151_prerender_boundary import (
    patch,GUARD,INCLUDE,BEFORE,AFTER,PIXEL)
from run_stage151_native_prerender_boundary import (
    BoundaryError,verify)

SOURCE=(b'#include "vpd_stage150_dynamic_oam_frame_probe.h"\n'
        b"vpd_ppu_probe::stage141_before_reset(PPU_status);\n"
        b"PPU_status = 0;\n"
        b"vpd_ppu_probe::stage141_after_reset(PPU_status);\n"
        b"vpd_ppu_probe::stage150_pixel("
        b"sl,rasterpos,oamcounts[renderslot],PPU_status,*ptr,"
        b"Sprite16,pixelcolor,havepixel,pixel & 3);\n")


def witness(mode,*,negative=False,values=None):
    if values is None:
        values=(1,0,8,8,5,1 if negative else 0)
    return ("VPD_STAGE151_NATIVE_PRERENDER_OAM_BOUNDARY_%s "
            "case=%s resets_between_frames=%d reset_after_status=%d "
            "before_samples=%d after_samples=%d cpu_writes=%d "
            "invalid=%d synthetic_only=yes "
            "original_game_frame_timing_proven=no"%
            ("REJECT" if negative else "PASS",mode,*values))


class SourceLocation(unittest.TestCase):
    def test_pinned_reset_and_native_xbuf_sites_guarded(self):
        for source in (SOURCE,SOURCE.replace(b"\n",b"\r\n")):
            with self.subTest(crlf=b"\r\n" in source):
                output=patch(source)
                self.assertEqual(output.count(GUARD),4)
                for call in (b"stage151_before_reset(",
                             b"stage151_after_reset(",
                             b"stage151_after_pixel("):
                    self.assertEqual(output.count(call),1)
                self.assertLess(output.index(b"stage151_before_reset("),
                                output.index(b"PPU_status = 0;"))
                self.assertGreater(output.index(b"stage151_after_reset("),
                                   output.index(b"PPU_status = 0;"))
                with self.assertRaises(ValueError):patch(output)
                if b"\r\n" in source:
                    self.assertEqual(output.count(b"\r\n"),output.count(b"\n"))

    def test_source_gates_fail_closed_on_modified_hooks(self):
        for marker in (INCLUDE,BEFORE,AFTER,PIXEL,b"PPU_status = 0;"):
            with self.subTest(marker=marker),self.assertRaises(ValueError):
                patch(SOURCE.replace(marker,b"invalid_native_site"))
        with self.assertRaises(TypeError):patch("fake C++ source")


class SourceCertificates(unittest.TestCase):
    def test_both_positive_and_expected_negative(self):
        for mode in ("activate_ninth","preserve_eight"):
            with self.subTest(mode=mode):
                report=verify(witness(mode),mode)
                self.assertEqual(report["boundary_reset"],1)
                self.assertEqual(report["before_samples"],8)
                self.assertEqual(report["after_samples"],8)
                self.assertFalse(report["original_game_frame_timing_proven"])
        rejected=verify(witness("preserve_eight",negative=True),
                        "preserve_eight",reject=True)
        self.assertTrue(rejected["rejected"])

    def test_corrupt_missing_duplicate_or_wrong_mode_rejected(self):
        for mode in ("activate_ninth","preserve_eight"):
            valid=witness(mode)
            bad=(
                "",valid+"\n"+valid,valid+"\n"+witness(mode,negative=True),
                valid.replace("resets_between_frames=1",
                              "resets_between_frames=0"),
                valid.replace("resets_between_frames=1",
                              "resets_between_frames=2"),
                valid.replace("reset_after_status=0",
                              "reset_after_status=32"),
                valid.replace("before_samples=8","before_samples=7"),
                valid.replace("after_samples=8","after_samples=9"),
                valid.replace("cpu_writes=5","cpu_writes=4"),
                valid.replace("invalid=0","invalid=1"),
                valid.replace("synthetic_only=yes","synthetic_only=no"),
                valid.replace("original_game_frame_timing_proven=no",
                              "original_game_frame_timing_proven=yes"),
            )
            for i,log in enumerate(bad):
                with self.subTest(mode=mode,mutation=i):
                    with self.assertRaises(BoundaryError):verify(log,mode)
        with self.assertRaises(BoundaryError):
            verify(witness("activate_ninth"),"preserve_eight")
        with self.assertRaises(BoundaryError):
            verify(witness("preserve_eight"),"preserve_eight",reject=True)


@unittest.skipUnless(shutil.which("c++"),"C++ compiler unavailable")
class CompiledBoundary(unittest.TestCase):
    def test_actual_boundary_sequence_and_missing_reset(self):
        source=r'''
#include "vpd_newppu_raw_step_probe.h"
#include "vpd_stage149_cpu_oam_probe.h"
#include "vpd_stage150_dynamic_oam_frame_probe.h"
#include "vpd_stage151_prerender_boundary.h"
#include <cstdlib>
int main(int argc,char**argv){
 if(argc<3)return 3;
 const bool active=argv[1][0]=='a';
 const bool omit=argv[2][0]=='o';
 const bool broken=argv[2][0]=='b';
 setenv("VPD_STAGE149_OAM_WRITES_PROBE","1",1);
 setenv("VPD_STAGE149_OAM_WRITES_CASE",
        active?"activate_ninth":"preserve_eight",1);
 setenv("VPD_STAGE150_DYNAMIC_OAM_PROBE","1",1);
 setenv("VPD_STAGE150_DYNAMIC_OAM_CASE",
        active?"activate_ninth":"preserve_eight",1);
 setenv("VPD_STAGE151_BOUNDARY_PROBE","1",1);
 vpd_ppu_probe::Stage149OamAudit& cpu=vpd_ppu_probe::stage149_oam_state();
 vpd_ppu_probe::Stage150Audit& ppu=vpd_ppu_probe::stage150_state();
 cpu.writes=5;cpu.addr_writes=1;cpu.high_reads=1;cpu.emitted=true;
 ppu.before.samples=8;ppu.before.evaluated=true;
 if(!omit){
   vpd_ppu_probe::stage151_before_reset(0);
   vpd_ppu_probe::stage151_after_reset(broken?32:0);
 }
 ppu.after.samples=8;ppu.after.evaluated=true;ppu.emitted=true;
 vpd_ppu_probe::stage151_after_pixel();
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"a.cpp";exe=Path(td)/"run"
            src.write_text(source)
            compiled=subprocess.run([
                "c++","-std=c++11","-Wall","-Wextra","-Werror",
                "-pedantic",
                "-DVPD_NATIVE_SYNTHETIC_OAM_CPU_WRITES",
                "-DVPD_NATIVE_SYNTHETIC_DYNAMIC_OAM_FRAMES",
                "-DVPD_NATIVE_SYNTHETIC_OAM_PRERENDER_BOUNDARY",
                "-I",str(ROOT/"tools"),str(src),"-o",str(exe)],
                capture_output=True,text=True)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            for mode,label in (("activate_ninth","a"),
                               ("preserve_eight","p")):
                for variant in ("ok","omit","broken"):
                    with self.subTest(mode=mode,variant=variant):
                        result=subprocess.run([str(exe),label,variant],
                                              capture_output=True,text=True)
                        self.assertEqual(result.returncode,0,result.stderr)
                        self.assertTrue(verify(
                            result.stderr,mode,reject=variant!="ok"))


if __name__=="__main__":
    unittest.main()
