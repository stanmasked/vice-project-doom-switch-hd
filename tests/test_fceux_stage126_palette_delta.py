"""Stage126: single-entry synthetic palette interventions and real C++ witness."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from make_stage124_native_quadrant_rom import make_rom, initialization
from run_stage126_palette_delta import (
    expected_colors, verify_delta_report, verify_negative, verify_sweep,
    PaletteDeltaError,
)

BASE = (176, 177, 178, 179)


def marker(target):
    return (
        "VPD_STAGE126_NATIVE_PALETTE_DELTA_PASS "
        "target=%d samples=16,16,16,16 indices=3,7,11,15 "
        "base=176,177,178,179 observed=%s changed_quadrants=1 invalid=0 "
        "actual_fceux_xbuf=yes synthetic_only=yes "
        "original_game_palette_proven=no" %
        (target, ",".join(map(str, expected_colors(target))))
    )


class PaletteGenerator(unittest.TestCase):
    def test_exactly_one_6502_palette_value_changes_in_each_prg_bank(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline = root/"baseline.nes"
            make_rom(baseline)
            base = baseline.read_bytes()
            self.assertEqual(len(base), 49168)
            for q in range(4):
                mutant = root / ("q%d.nes" % q)
                make_rom(mutant, targeted_quadrant=q)
                blob = mutant.read_bytes()
                self.assertEqual(blob[:16], base[:16])
                self.assertEqual(blob[-16384:], base[-16384:])
                self.assertEqual(len(blob), len(base))
                changed = [i for i, (a, b) in enumerate(zip(base, blob)) if a != b]
                self.assertEqual(len(changed), 4)
                self.assertEqual(len({(i-16) % 8192 for i in changed}), 1)
                self.assertEqual({base[i] for i in changed}, {0x30+q})
                self.assertEqual({blob[i] for i in changed}, {0x34+q})
                self.assertEqual(
                    initialization(targeted_quadrant=q).count(
                        bytes((0xA9, 0x34+q, 0x8D, 7, 0x20))), 1
                )

    def test_invalid_interventions_fail_before_rom_written(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)/"invalid.nes"
            for bad in (-1, 4, True, 1.0, "2"):
                with self.subTest(value=bad), self.assertRaises(ValueError):
                    make_rom(out, targeted_quadrant=bad)
                self.assertFalse(out.exists())
            for kwargs in (dict(targeted_quadrant=0, attribute=0),
                           dict(targeted_quadrant=0, distinct_palette=False),
                           dict(targeted_quadrant=0, switch=False)):
                with self.subTest(options=kwargs), self.assertRaises(ValueError):
                    make_rom(out, **kwargs)
                self.assertFalse(out.exists())


class NativeCertificates(unittest.TestCase):
    def test_four_strict_positive_reports_and_paired_sweep(self):
        baseline = {"xbuf_colors": list(BASE),
                    "original_game_palette_proven": False}
        records = [(q, verify_delta_report(marker(q), q)) for q in range(4)]
        self.assertEqual(verify_sweep(records, baseline)["native_pixel_samples"], 256)
        self.assertEqual([r["observed"][q] for q, r in records],
                         [180, 181, 182, 183])

    def test_forged_or_mismatched_reports_rejected(self):
        for target in range(4):
            good = marker(target)
            mutations = (
                "", good+"\n"+good,
                good.replace("changed_quadrants=1", "changed_quadrants=2"),
                good.replace("invalid=0", "invalid=1"),
                good.replace("samples=16,16,16,16", "samples=16,16,16,15"),
                good.replace("actual_fceux_xbuf=yes", "actual_fceux_xbuf=no"),
                good.replace("original_game_palette_proven=no",
                             "original_game_palette_proven=yes"),
                good.replace("observed=", "observed=0,"),
                good + "\nVPD_STAGE126_REJECTED_PALETTE_DELTA target=0 invalid=1",
            )
            for bad in mutations:
                with self.subTest(target=target, report=bad[-40:]):
                    with self.assertRaises(PaletteDeltaError):
                        verify_delta_report(bad, target)
            with self.assertRaises(PaletteDeltaError):
                verify_delta_report(good, (target+1)%4)

    def test_rejection_of_nonintervention_is_observed(self):
        fail = ("VPD_STAGE126_REJECTED_PALETTE_DELTA "
                "target=0 invalid=16 observed=176,177,178,179 "
                "samples=16,16,16,16 synthetic_only=yes")
        self.assertTrue(verify_negative(fail, 0)["rejected"])
        for bad in ("", fail+"\n"+fail, fail+"\n"+marker(0),
                    fail.replace("invalid=16", "invalid=0"),
                    fail.replace("observed=176,177,178,179",
                                 "observed=180,177,178,179"),
                    fail.replace("synthetic_only=yes", "synthetic_only=no")):
            with self.subTest(report=bad[-80:]), self.assertRaises(PaletteDeltaError):
                verify_negative(bad, 0)
        for invalid in (-1, 4, True, 1.5, "1"):
            with self.assertRaises(PaletteDeltaError):
                expected_colors(invalid)


@unittest.skipUnless(shutil.which("c++"), "Native C++ compiler unavailable")
class NativeCpp(unittest.TestCase):
    def test_native_header_all_targets_and_missing_intervention(self):
        code = r"""
#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main(int argc,char** argv) {
 if(argc<2)return 2;
 setenv("VPD_STAGE124_QUADRANT_PROBE","1",1);
 setenv("VPD_STAGE126_TARGET_QUADRANT",argv[1],1);
 setenv("VPD_STAGE110_MIDFRAME_CHR_PROBE","1",1);
 const unsigned target=(unsigned)(argv[1][0]-'0');
 const bool unchanged=argc>2;
 vpd_ppu_probe::stage110_register_write(2,0);
 for(unsigned sl=1;sl<=190;++sl) {
  for(unsigned x=0;x<256;++x) {
   if(sl==104 && x==36)vpd_ppu_probe::stage110_register_write(2,1);
   const unsigned nt=0x2000U+(((sl/8U)%30U)<<5)+(x/8U);
   const unsigned q=((nt&0x40U)?2U:0U)+((nt&2U)?1U:0U);
   const unsigned addr=0x23C0U+(nt&0x0C00U)+
              ((nt&0x0380U)>>4)+((nt&0x001CU)>>2);
   const unsigned color=(q==target&&!unchanged)?(0x34U+target):(0x30U+q);
   vpd_ppu_probe::stage124_pixel(sl,x/8U,x%8U,nt,addr,0xE4U,
       2U*q,4U*q,3U,4U*q+3U,color,0x80U|color);
   vpd_ppu_probe::stage110_raster_pixel(
       sl,sl<105?0U:3U,0x80U|color);
   ++vpd_ppu_probe::channel().internal_tick_units;
  }
 }
 return 0;
}
"""
        with tempfile.TemporaryDirectory() as td:
            src, exe = Path(td)/"palette_delta.cpp", Path(td)/"palette_delta"
            src.write_text(code)
            p = subprocess.run([
                "c++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                "-pedantic", "-DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR",
                "-DVPD_NATIVE_SYNTHETIC_QUADRANT_COLORS",
                "-I", str(ROOT/"tools"), str(src), "-o", str(exe),
            ], text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            for target in range(4):
                run = subprocess.run([str(exe), str(target)],
                                     text=True, capture_output=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                verify_delta_report(run.stderr, target)
                self.assertNotIn("VPD_STAGE124_NATIVE_QUADRANTS_PASS", run.stderr)
            negative = subprocess.run([str(exe), "0", "unchanged"],
                                      text=True, capture_output=True)
            self.assertEqual(negative.returncode, 0, negative.stderr)
            self.assertTrue(verify_negative(negative.stderr, 0)["rejected"])


if __name__ == "__main__":
    unittest.main()
