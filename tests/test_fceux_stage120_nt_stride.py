"""Stage120 independent NT address-stride proof and page-alias mutation."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_stage120_nt_stride import (
    NametableStrideError, verify_stride_report, verify_stride_sweep,
)
from run_stage119_native_nametable import verify_report as verify_stage119, FINES

STAGE119 = (
    "VPD_STAGE119_NATIVE_NAMETABLE_PASS fine1={fine} fine2={second} "
    "coarse1=0 coarse2=1 write_sl1=104 write_sl2=105 "
    "sample_sl1=105 sample_sl2=106 nametable0_x0=0 nametable1_x0=1 "
    "pattern0_x0=0 pattern1_x0=3 first_color=15 second_color=48 "
    "nt_address0=2004 nt_address1=2005 samples_per_row=16 "
    "odd_first=7 odd_second=9 invalid=0 "
    "real_fceux_xbuf=yes synthetic_only=yes "
    "original_game_coarse_scroll_proven=no"
)
STAGE120 = (
    "VPD_STAGE120_NATIVE_NT_STRIDE_PASS "
    "fine1={fine} fine2={second} nt_addr0=2004 nt_addr1=2005 "
    "samples0=16 samples1=16 transitions0=2 transitions1=2 "
    "invalid=0 real_fceux_nt_to_xbuf=yes synthetic_only=yes "
    "original_game_nt_stride_proven=no"
)


def mocked(fine):
    return (STAGE120 + "\n" + STAGE119).format(fine=fine, second=8-fine)


class Report(unittest.TestCase):
    def test_four_matching_native_proofs(self):
        records = []
        for fine in FINES:
            log = mocked(fine)
            records.append((fine, verify_stride_report(
                log, fine, verify_stage119(log, fine))))
        result = verify_stride_sweep(records)
        self.assertEqual(result["total_samples"], 128)
        self.assertEqual(result["total_tile_transitions"], 16)
        self.assertFalse(result["original_game_nt_stride_proven"])

    def test_native_row_origin_is_not_hardcoded_to_2000(self):
        # The renderer can be on a vertically advanced tile row.
        # Its *tile columns* still have strict increments and are
        # bound between Stage119 and Stage120.
        good = mocked(3)
        moved = (good.replace("nt_address0=2004", "nt_address0=20A4")
                     .replace("nt_address1=2005", "nt_address1=20A5")
                     .replace("nt_addr0=2004", "nt_addr0=20A4")
                     .replace("nt_addr1=2005", "nt_addr1=20A5"))
        origin = verify_stage119(moved, 3)
        self.assertEqual(verify_stride_report(moved, 3, origin)["addresses"],
                         [0x20A4, 0x20A5])

    def test_mutations_fail_closed_even_if_stage119_still_passes(self):
        good = mocked(3)
        mutations = (
            "", good + "\n" + good,
            good.replace("nt_addr0=2004", "nt_addr0=2404"),
            good.replace("nt_addr1=2005", "nt_addr1=2405"),
            good.replace("transitions0=2", "transitions0=1"),
            good.replace("transitions1=2", "transitions1=3"),
            good.replace("samples1=16", "samples1=15"),
            good.replace("fine1=3", "fine1=5", 1),
            good.replace("original_game_nt_stride_proven=no",
                         "original_game_nt_stride_proven=yes"),
            good + "\nVPD_STAGE120_REJECTED_NT_STRIDE invalid=1",
            STAGE119.format(fine=3, second=5),
        )
        for bad in mutations:
            with self.subTest(log=bad[-90:]), self.assertRaises(NametableStrideError):
                verify_stride_report(bad, 3, verify_stage119(good, 3))

    def test_reject_cross_stage_inconsistent_source_and_sweep(self):
        good = mocked(3)
        origin = verify_stage119(good, 3)
        for modified in (
            {**origin, "first_nametable_source_address": 0x2400},
            {**origin, "second_nametable_source_address": 0x2401},
            {**origin, "original_game_coarse_scroll_proven": True}, None,
        ):
            with self.assertRaises(NametableStrideError):
                verify_stride_report(good, 3, modified)
        proper = [(f, verify_stride_report(
            mocked(f), f, verify_stage119(mocked(f), f))) for f in FINES]
        for records in (proper[::-1], proper[:-1], proper + proper[:1]):
            with self.assertRaises(NametableStrideError):
                verify_stride_sweep(records)


@unittest.skipUnless(shutil.which("c++"), "Native C++ compiler unavailable")
class Native(unittest.TestCase):
    def test_stage120_detects_hidden_nt_page_alias_without_breaking_stage119(self):
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
   unsigned addr=0x2000U+tile+(second?1U:0U);
   // This is the new negative control: parity, ID, planes, XBuf all
   // remain correct. Only buffered source address changes to its alias.
   if(argc>1&&sl==106&&x==40)addr+=0x400U;
   vpd_ppu_probe::stage119_pixel(
      sl,x/8,x%8,tile,bgpx,scroll,second?1U:0U,
      nt,addr,plane,plane,nt?3U:0U,nt?48U:15U);
   vpd_ppu_probe::stage110_raster_pixel(
      sl,sl<105?0U:(nt?3U:0U),nt?48U:15U);
   ++vpd_ppu_probe::channel().internal_tick_units;
  }
 }
 return 0;
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            source, binary = Path(tmp) / "stride.cpp", Path(tmp) / "stride"
            source.write_text(code)
            cc = subprocess.run(
                ["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                 "-pedantic", "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                 "-DVPD_NATIVE_SYNTHETIC_NAMETABLE_IDS",
                 "-I", str(ROOT/"tools"), str(source), "-o", str(binary)],
                text=True, capture_output=True)
            self.assertEqual(cc.returncode, 0, cc.stderr)
            clean = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(clean.returncode, 0, clean.stderr)
            self.assertIn("VPD_STAGE119_NATIVE_NAMETABLE_PASS", clean.stderr)
            self.assertIn("VPD_STAGE120_NATIVE_NT_STRIDE_PASS", clean.stderr)
            verify_stride_report(clean.stderr, 3, verify_stage119(clean.stderr, 3))
            alias = subprocess.run([str(binary), "alias"],
                                   capture_output=True, text=True)
            self.assertEqual(alias.returncode, 0, alias.stderr)
            # Previous stage would have accepted the falsified $2406 source.
            self.assertIn("VPD_STAGE119_NATIVE_NAMETABLE_PASS", alias.stderr)
            self.assertIn("VPD_STAGE120_REJECTED_NT_STRIDE", alias.stderr)
            self.assertNotIn("VPD_STAGE120_NATIVE_NT_STRIDE_PASS", alias.stderr)
            with self.assertRaises(NametableStrideError):
                verify_stride_report(alias.stderr, 3, verify_stage119(alias.stderr, 3))


if __name__ == "__main__":
    unittest.main()
