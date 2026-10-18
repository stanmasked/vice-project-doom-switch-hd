"""Stage149: native OAM CPU register parser, source injection and C++ gates.

Mock C++ runs do not count as native FCEUX evidence; only the pinned
native CI run can produce the Stage149 aggregated marker.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))

from inject_fceux_stage149_vblank_oam_cpu import patch,GUARD,EXTRA
from run_stage149_native_vblank_oam import (
    MODES,PASS,REJECT,OamWriteError,verify,verify_wrong_case,verify_sweep)

SOURCE=(b'#include "vpd_newppu_raw_step_probe.h"\n'
        b'static DECLFR(A2002) {\n'
        b'\tif (newppu) vpd_ppu_probe::observe_native_ppustatus_read(\n'
        b'\t\t\t(ret & 0x80) != 0, vpd_2002_before,\n'
        b'\t\t\t(PPU_status & 0x80) != 0);\n'
        b'}\nstatic DECLFR(A2004) {\n}\n'
        b'static DECLFW(B2003) {\n'
        b'\tPPUSPL = V & 0x7;\n'
        b'}\nstatic DECLFW(B2004) {\n'
        b'\tif(newppu) {\n'
        b'\t\tSPRAM[PPU[3]] = V;\n'
        b'\t\tPPU[3] = (PPU[3] + 1) & 0xFF;\n'
        b'\t}\n}\nstatic DECLFW(B2005) {\n}\n'
        b'vpd_ppu_probe::stage141_pixel(')


def witness(mode,*,reject=False,values=None,invalid=0):
    values=values or ((160,120,2,0,64,0) if mode=="activate_ninth"
                      else (64,255,255,255,255,227))
    header=REJECT if reject else PASS
    return (header+" case=%s status_high_read=yes oamaddr=31 writes=5 "
            "first_oam=31 last_oam=35 "
            "oam7_x=%d oam8_y=%d oam8_tile=%d oam8_attr=%d oam8_x=%d "
            "attr_stored=%d invalid=%d synthetic_only=yes "
            "original_game_oam_writes_proven=no" %
            (mode,*values,invalid))


class SourceHooks(unittest.TestCase):
    def test_exact_source_locations_and_newppu_increment(self):
        for source in (SOURCE,SOURCE.replace(b"\n",b"\r\n")):
            with self.subTest(crlf=b"\r\n" in source):
                actual=patch(source)
                self.assertEqual(actual.count(GUARD),4)
                self.assertEqual(actual.count(EXTRA),1)
                for name in (b"stage149_status_read(",
                             b"stage149_oam_address(",
                             b"stage149_oam_data("):
                    self.assertEqual(actual.count(name),1)
                self.assertIn(b"PPU[3],V,SPRAM[PPU[3]],newppu);",actual)
                if b"\r\n" in source:
                    self.assertEqual(actual.count(b"\n"),actual.count(b"\r\n"))
                with self.assertRaises(ValueError):
                    patch(actual)

    def test_missing_or_forged_pinned_hooks_fail_closed(self):
        for anchor in (b"static DECLFR(A2002) {",
                       b"static DECLFR(A2004) {",
                       b"static DECLFW(B2003) {",
                       b"static DECLFW(B2004) {",
                       b"static DECLFW(B2005) {",
                       b"vpd_ppu_probe::stage141_pixel(",
                       b"SPRAM[PPU[3]] = V;",
                       b"PPUSPL = V & 0x7;",
                       b"(PPU_status & 0x80) != 0);"):
            with self.subTest(anchor=anchor):
                with self.assertRaises(ValueError):
                    patch(SOURCE.replace(anchor,b"not_the_pinned_source"))
        with self.assertRaises(TypeError):
            patch(SOURCE.decode("ascii"))


class Certificates(unittest.TestCase):
    def test_both_native_cases_and_total_cpu_writes(self):
        reports=[(mode,verify(witness(mode),mode)) for mode in MODES]
        self.assertEqual(verify_sweep(reports)["register_writes"],10)
        self.assertEqual(reports[0][1]["oam_values"],(160,120,2,0,64))
        self.assertEqual(reports[1][1]["attr_stored"],227)
        self.assertEqual(verify_wrong_case(
            witness("preserve_eight",reject=True,
                    values=(160,120,2,0,64,0),invalid=5)
            )["mismatched_cpu_written_bytes"],5)

    def test_forged_control_and_partial_log_rejected(self):
        for mode in MODES:
            real=witness(mode)
            for i,damaged in enumerate((
                "",real+"\n"+real,real+"\n"+REJECT,
                real.replace("status_high_read=yes","status_high_read=no"),
                real.replace("writes=5","writes=4"),
                real.replace("oamaddr=31","oamaddr=32"),
                real.replace("first_oam=31","first_oam=30"),
                real.replace("last_oam=35","last_oam=34"),
                real.replace("attr_stored=","attr_stored=0"),
                real.replace("invalid=0","invalid=1"),
                real.replace("synthetic_only=yes","synthetic_only=no"),
                real.replace("original_game_oam_writes_proven=no",
                             "original_game_oam_writes_proven=yes"),
            )):
                with self.subTest(mode=mode,mutation=i):
                    with self.assertRaises(OamWriteError):
                        verify(damaged,mode)
        with self.assertRaises(OamWriteError):
            verify(witness("activate_ninth"),"preserve_eight")
        with self.assertRaises(OamWriteError):
            verify_wrong_case(witness("preserve_eight"))
        with self.assertRaises(OamWriteError):
            verify_wrong_case(witness("preserve_eight",reject=True,
                           values=(160,120,2,0,64,0),invalid=4))


@unittest.skipUnless(shutil.which("c++"),"C++ compiler unavailable")
class CompiledObserver(unittest.TestCase):
    def test_native_header_accepts_real_sequence_and_rejects_faults(self):
        source=r'''
#include "vpd_newppu_raw_step_probe.h"
#include "vpd_stage149_cpu_oam_probe.h"
#include <cstdlib>
int main(int argc,char**argv) {
    if(argc<3)return 3;
    const bool actual=argv[1][0]=='a';
    const bool lie=argv[2][0]=='l';
    const bool forget=argv[2][0]=='n';
    const bool badattr=argv[2][0]=='m';
    setenv("VPD_STAGE149_OAM_WRITES_PROBE","1",1);
    setenv("VPD_STAGE149_OAM_WRITES_CASE",
           lie || !actual?"preserve_eight":"activate_ninth",1);
    vpd_ppu_probe::channel().internal_tick_units=400;
    if(!forget)vpd_ppu_probe::stage149_status_read(true);
    vpd_ppu_probe::channel().internal_tick_units=420;
    vpd_ppu_probe::stage149_oam_address(31,31,true);
    const unsigned activate[]={160,120,2,0,64};
    const unsigned preserve[]={64,255,255,255,255};
    const unsigned* data=actual?activate:preserve;
    for(unsigned i=0;i<5;++i){
        vpd_ppu_probe::channel().internal_tick_units+=18;
        unsigned stored=i==3?(data[i]&0xE3U):data[i];
        if(badattr && i==3)stored++;
        vpd_ppu_probe::stage149_oam_data(31+i,data[i],stored,true);
    }
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"probe.cpp"
            binpath=Path(td)/"probe"
            src.write_text(source)
            build=subprocess.run([
                "c++","-std=c++11","-Wall","-Wextra","-Werror","-pedantic",
                "-DVPD_NATIVE_SYNTHETIC_OAM_CPU_WRITES",
                "-I",str(ROOT/"tools"),str(src),"-o",str(binpath)
            ],capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            for mode,flag in (("activate_ninth","a"),
                              ("preserve_eight","p")):
                p=subprocess.run([str(binpath),flag,"ok"],
                                 capture_output=True,text=True)
                self.assertEqual(p.returncode,0,p.stderr)
                verify(p.stderr,mode)
            for args in (("a","lie"),("a","nohigh"),("p","mask")):
                with self.subTest(args=args):
                    p=subprocess.run([str(binpath),*args],
                                     capture_output=True,text=True)
                    self.assertEqual(p.returncode,0,p.stderr)
                    self.assertEqual(p.stderr.count(REJECT),1,p.stderr)
                    self.assertNotIn(PASS,p.stderr)
            lied=subprocess.run([str(binpath),"a","lie"],
                                capture_output=True,text=True)
            verify_wrong_case(lied.stderr)


if __name__=="__main__":
    unittest.main()
