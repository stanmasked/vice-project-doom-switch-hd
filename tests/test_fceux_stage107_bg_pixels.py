"""Stage107 original synthetic mapper4 and native framebuffer proof regressions."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from inject_fceux_stage107_bg_pixel_probe import patch_pixel_sink, CALL
from make_stage107_synthetic_chr_pixel_rom import make_rom, program
from run_stage107_native_bg_pixels import verify_report, verify_pair, PixelProofError

MOCK = (b'#include "vpd_newppu_raw_step_probe.h"\n'
        b'#ifdef VPD_NATIVE_SYNTHETIC_PRECLEAR\n#endif\n'
        b'\t\t*ptr = PaletteAdjustPixel(pixelcolor);\n')
MARKER = ("VPD_STAGE107_NATIVE_BG_PIXEL_PASS sampled=32768 "
          "bg_zero={zero} bg_nonzero={nonzero} final_fnv64={hash} invalid={invalid} "
          "synthetic_only=yes original_pixel_proof=no")


class SourcePatch(unittest.TestCase):
    def test_exact_assignment_and_disabled_compilation_guard(self):
        raw = patch_pixel_sink(MOCK)
        self.assertEqual(raw.count(CALL), 1)
        self.assertIn(b'if (renderbgnow && renderbg && !havepixel)', raw)
        self.assertIn(b'#ifdef VPD_NATIVE_SYNTHETIC_BG_PIXELS', raw)

    def test_reject_ambiguous_missing_duplicate(self):
        for source in (MOCK + MOCK, MOCK.replace(b'*ptr', b'*target'),
                       patch_pixel_sink(MOCK), MOCK.replace(
                           b'VPD_NATIVE_SYNTHETIC_PRECLEAR', b'missing')):
            with self.subTest(source=source[:35]), self.assertRaises(ValueError):
                patch_pixel_sink(source)

    def test_preserve_crlf(self):
        result = patch_pixel_sink(MOCK.replace(b'\n', b'\r\n'))
        self.assertEqual(result.count(b'\n'), result.count(b'\r\n'))


class RomControls(unittest.TestCase):
    def test_mapper4_rom_is_original_and_only_bank_byte_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a.nes', Path(tmp) / 'b.nes'
            make_rom(a, 0); make_rom(b, 1)
            data = a.read_bytes()
            other = b.read_bytes()
            self.assertEqual(data[:8], b'NES\x1a\x02\x02\x40\x00')
            self.assertEqual(len(data), 49168)
            self.assertEqual(data[-16384 + 1024:-16384 + 2048], b'\xff' * 1024)
            self.assertEqual(data[-16384:], other[-16384:])
            self.assertEqual(len(program(0)), len(program(1)))
            self.assertEqual(sum(x != y for x, y in zip(data, other)), 4)


class ReportControls(unittest.TestCase):
    def test_two_distinct_real_framebuffer_hashes_required(self):
        a = verify_report(MARKER.format(zero=32768, nonzero=0, hash=1, invalid=0))
        b = verify_report(MARKER.format(zero=0, nonzero=32768, hash=2, invalid=0))
        self.assertTrue(verify_pair(a, b))
        for zero, nonzero, checksum in ((32768, 0, 2),
                                        (10000, 22768, 3),
                                        (0, 32768, 1)):
            bad = verify_report(MARKER.format(zero=zero, nonzero=nonzero,
                                               hash=checksum, invalid=0))
            with self.assertRaises(PixelProofError):
                verify_pair(a, bad)

    def test_invalid_or_duplicated_marker_rejected(self):
        good = MARKER.format(zero=32768, nonzero=0, hash=1, invalid=0)
        for s in ('', good + '\n' + good,
                  good.replace('invalid=0', 'invalid=1'),
                  good.replace('bg_zero=32768', 'bg_zero=30000'),
                  good.replace('original_pixel_proof=no', 'original_pixel_proof=yes')):
            with self.subTest(value=s[:30]), self.assertRaises(PixelProofError):
                verify_report(s)


@unittest.skipUnless(shutil.which('c++'), 'C++ compiler unavailable')
class HeaderSmoke(unittest.TestCase):
    def test_native_cpp11_header_aggregates_actual_byte_values(self):
        code = '''#include "vpd_newppu_raw_step_probe.h"
#include <cstdlib>
int main() {
 setenv("VPD_STAGE107_BG_PIXEL_PROBE", "1", 1);
 for(int n=0;n<32768;++n)
  vpd_ppu_probe::observe_native_bg_pixel(n & 1 ? 3 : 0, n & 1 ? 48 : 15);
 return 0;
}'''
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / 'a.cpp', Path(tmp) / 'a'
            src.write_text(code)
            p = subprocess.run(['c++', '-std=c++11', '-Wall', '-Wextra',
                                '-Werror', '-pedantic',
                                '-DVPD_NATIVE_SYNTHETIC_BG_PIXELS',
                                '-I', str(ROOT / 'tools'), str(src), '-o', str(dst)],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            p = subprocess.run([str(dst)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(verify_report(p.stderr)['bg_nonzero'], 16384)


if __name__ == '__main__':
    unittest.main()
