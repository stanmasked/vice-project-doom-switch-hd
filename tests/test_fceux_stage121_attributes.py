"""Stage121 fail-closed attribute-fetch and pixel-index provenance regression."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_stage120_nt_stride import verify_stride_report
from audit_stage121_attributes import (
    AttributeEvidenceError, expected_attribute_address,
    verify_attribute_report, verify_attribute_sweep,
)
from inject_fceux_stage119_nametable_pixels import patch as stage119_patch
from inject_fceux_stage121_attributes import patch as stage121_patch, GUARD
from run_stage119_native_nametable import verify_report as stage119_report
from test_fceux_stage119_nametable import SOURCE as STAGE118_SOURCE, PASS as STAGE119

STAGE120 = (
    "VPD_STAGE120_NATIVE_NT_STRIDE_PASS fine1={fine} fine2={second} "
    "nt_addr0=2000 nt_addr1=2001 samples0=16 samples1=16 "
    "transitions0=2 transitions1=2 invalid=0 "
    "real_fceux_nt_to_xbuf=yes synthetic_only=yes "
    "original_game_nt_stride_proven=no"
)
STAGE121 = (
    "VPD_STAGE121_NATIVE_ATTRIBUTE_PASS fine1={fine} fine2={second} "
    "attr_addr0=23C0 attr_addr1=23C0 samples0=16 samples1=16 "
    "invalid=0 buffered_attribute_to_pixel=yes synthetic_only=yes "
    "original_game_palette_proven=no"
)


def good_log(fine):
    return "\n".join((STAGE119, STAGE120, STAGE121)).format(
        fine=fine, second=8-fine)


def verify(log, fine):
    identity = stage119_report(log, fine)
    stride = verify_stride_report(log, fine, identity)
    return verify_attribute_report(log, fine, identity, stride)


class Source(unittest.TestCase):
    def test_real_pinned_attribute_fetch_and_bgdata_consumption(self):
        patched = stage121_patch(stage119_patch(STAGE118_SOURCE))
        self.assertEqual(patched.count(GUARD), 8)
        self.assertEqual(patched.count(b"vpd_ppu_probe::stage121_pixel("), 1)
        self.assertIn(b"vpd_stage121_ataddr = RefreshAddr", patched)
        self.assertIn(b"vpd_stage121_atraw = at", patched)
        self.assertIn(b"vpd_stage121_shift = ((ppur.vt & 2)", patched)
        self.assertIn(b"bgdata.main[bgtile].at, pixel & 3", patched)
        self.assertIn(b"pixel);", patched)
        self.assertEqual(patched.count(b"\r\n"), patched.count(b"\n"))
        with self.assertRaises(ValueError):
            stage121_patch(patched)

    def test_missing_and_duplicated_attribute_hooks_rejected(self):
        ready = stage119_patch(STAGE118_SOURCE)
        for broken in (
            ready + ready,
            ready.replace(b"at = CALL_PPUREAD(RefreshAddr);", b"no_read();"),
            ready.replace(b"at <<= 2;", b"at = 0;"),
            ready.replace(b"unsigned vpd_stage119_ntaddr = 0;", b"missing"),
            ready.replace(b"vpd_stage119_ntaddr = NTRefreshAddr", b"missing"),
            ready.replace(b"pixel & 3, *ptr);", b"not_the_renderer();"),
        ):
            with self.subTest(data=broken[-50:]), self.assertRaises(ValueError):
                stage121_patch(broken)
        with self.assertRaises(TypeError):
            stage121_patch(ready.decode("ascii"))


class Audit(unittest.TestCase):
    def test_exact_read_address_math(self):
        self.assertEqual(expected_attribute_address(0x2000), 0x23C0)
        self.assertEqual(expected_attribute_address(0x2003), 0x23C0)
        self.assertEqual(expected_attribute_address(0x2004), 0x23C1)
        self.assertEqual(expected_attribute_address(0x2080), 0x23D0)
        self.assertEqual(expected_attribute_address(0x2400), 0x27C0)
        for bad in (0x1FFF, 0x3000, True, 0x2000.0, "2000"):
            with self.assertRaises(AttributeEvidenceError):
                expected_attribute_address(bad)

    def test_full_phase_sweep_and_hostile_markers(self):
        records = []
        for fine in (1, 3, 5, 7):
            log = good_log(fine)
            records.append((fine, verify(log, fine)))
        self.assertEqual(verify_attribute_sweep(records)["total_samples"], 128)
        good = good_log(3)
        for bad in (
            "", good + "\n" + good,
            good.replace("attr_addr0=23C0", "attr_addr0=27C0"),
            good.replace("attr_addr1=23C0", "attr_addr1=23C1"),
            good.replace("samples0=16", "samples0=15"),
            good.replace("original_game_palette_proven=no",
                         "original_game_palette_proven=yes"),
            good + "\nVPD_STAGE121_REJECTED_ATTRIBUTE invalid=1",
            good.replace("fine1=3 fine2=5 attr_addr0", "fine1=5 fine2=3 attr_addr0"),
        ):
            with self.subTest(log=bad[-100:]), self.assertRaises(AttributeEvidenceError):
                verify_attribute_report(
                    bad, 3, stage119_report(good, 3),
                    verify_stride_report(good, 3, stage119_report(good, 3)))
        for invalid in (records[:3], records[::-1], records + records[:1]):
            with self.assertRaises(AttributeEvidenceError):
                verify_attribute_sweep(invalid)


@unittest.skipUnless(shutil.which("c++"), "Native C++ compiler unavailable")
class Native(unittest.TestCase):
    def test_cxx11_page_alias_attribute_fetch_rejected_only_by_stage121(self):
        code = r"""
#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main(int argc,char**) {
 setenv("VPD_STAGE119_NAMETABLE_PROBE","1",1);
 setenv("VPD_STAGE119_FIRST_FINE","3",1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 vpd_ppu_probe::stage110_register_write(2,0);
 vpd_ppu_probe::stage119_write(0,0);
 for(unsigned sl=1;sl<=107;++sl) {
  for(unsigned x=0;x<256;++x) {
   if(sl==104&&x==36)vpd_ppu_probe::stage110_register_write(2,1);
   if(sl==104&&x==39)vpd_ppu_probe::stage119_write(3,0);
   if(sl==105&&x==151)vpd_ppu_probe::stage119_write(5,1);
   const unsigned scroll=(sl>=106||(sl==105&&x>=151))?5:
                       (sl>=105||(sl==104&&x>=39)?3:0);
   const unsigned tile=(x+scroll)>>3;
   const unsigned bgpx=(x+scroll)&7U;
   const bool second=sl>=106;
   const unsigned nt=(tile+(second?1U:0U))&1U;
   const unsigned plane=nt?255U:0U;
   const unsigned ntaddr=0x2000U+tile+(second?1U:0U);
   unsigned attraddr=0x23C0U+(ntaddr&0x0C00U)+
             ((ntaddr&0x0380U)>>4)+((ntaddr&0x001CU)>>2);
   if(argc>1&&sl==106&&x==8)attraddr+=0x400U;
   const unsigned shift=((ntaddr&0x40U)?4U:0U)+
                        ((ntaddr&0x02U)?2U:0U);
   const unsigned raw=1U,decoded=((raw>>shift)&3U)<<2;
   const unsigned pattern=nt?3U:0U;
   vpd_ppu_probe::stage119_pixel(sl,x/8,x%8,tile,bgpx,
      scroll,second?1U:0U,nt,ntaddr,plane,plane,
      pattern,nt?48U:15U);
   vpd_ppu_probe::stage121_pixel(sl,x/8,x%8,ntaddr,attraddr,
      raw,shift,decoded,pattern,pattern|decoded);
   vpd_ppu_probe::stage110_raster_pixel(
      sl,sl<105?0U:pattern,nt?48U:15U);
   ++vpd_ppu_probe::channel().internal_tick_units;
  }
 }
 return 0;
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            src, exe = Path(tmp)/"attr.cpp", Path(tmp)/"attr"
            src.write_text(code)
            r = subprocess.run([
                "c++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                "-pedantic", "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                "-DVPD_NATIVE_SYNTHETIC_NAMETABLE_IDS",
                "-DVPD_NATIVE_SYNTHETIC_BG_ATTRIBUTES",
                "-I", str(ROOT/"tools"), str(src), "-o", str(exe),
            ], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            for args in ([], ["alias"]):
                run = subprocess.run([str(exe)]+args,
                                     capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertIn("VPD_STAGE119_NATIVE_NAMETABLE_PASS", run.stderr)
                self.assertIn("VPD_STAGE120_NATIVE_NT_STRIDE_PASS", run.stderr)
                if args:
                    self.assertIn("VPD_STAGE121_REJECTED_ATTRIBUTE", run.stderr)
                    self.assertNotIn("VPD_STAGE121_NATIVE_ATTRIBUTE_PASS", run.stderr)
                    with self.assertRaises(AttributeEvidenceError):
                        verify(run.stderr, 3)
                else:
                    self.assertIn("VPD_STAGE121_NATIVE_ATTRIBUTE_PASS", run.stderr)
                    self.assertEqual(verify(run.stderr, 3)["sampled_pixels"], 32)


if __name__ == "__main__":
    unittest.main()
