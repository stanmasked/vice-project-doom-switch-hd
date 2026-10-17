"""Stage106 pinned MMC3 CHR register switch/PPU-window synthetic regressions."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from inject_fceux_mmc3_chr_probe import (
    patch_mmc3, MMC3_CPP_GIT_BLOB, CALL, GUARD,
)
from make_stage106_synthetic_mmc3_rom import (
    make_mapper4_chr_toggle_rom, PROGRAM,
)
from run_stage106_native_mmc3_chr import verify_chr_write_report, Mmc3ProbeError

ROOT = Path(__file__).resolve().parents[1]
MOCK = (
    '#include "mapinc.h"\n'
    '#include "mmc3.h"\n'
    'DECLFW(MMC3_CMDWrite) {\n'
    '\tswitch (A & 0xE001) {\n'
    '\tcase 0x8001:\n'
    '\t{\n'
    '\t\tswitch (MMC3_cmd & 0x07) {\n'
    '\t\tcase 7:\n'
    '\t\t\tpwrap(0xA000, V);\n'
    '\t\t\tbreak;\n'
    '\t\t}\n'
    '\t\tbreak;\n'
    '\t}\n'
    '\tcase 0xA000:\n'
    '\t\tbreak;\n'
    '\t}\n'
    '}\n'
    'DECLFW(MMC3_IRQWrite) {\n'
    '}\n'
).encode()
MARKER = (
    "VPD_STAGE106_NATIVE_MMC3_CHR_PASS writes=4096 "
    "changed=4095 within_source_window=960 outside_source_window=3136 "
    "after_cpu_high_read=800 lag_min=1 lag_max=70 invalid=0 "
    "source_only=yes chr_pixel_causality_proven=no"
)


class Mmc3PinnedPatchTests(unittest.TestCase):
    def test_pinned_mmc3_git_blob_is_explicit(self):
        self.assertEqual(len(MMC3_CPP_GIT_BLOB), 40)
        self.assertRegex(MMC3_CPP_GIT_BLOB, r"^[0-9a-f]{40}$")

    def test_refuse_non_pinned_source_by_default(self):
        with self.assertRaisesRegex(ValueError, "pinned"):
            patch_mmc3(MOCK)

    def test_mock_patch_places_callback_only_inside_mmc3_8001(self):
        patched = patch_mmc3(MOCK, require_pinned=False)
        self.assertEqual(patched.count(GUARD), 2)
        self.assertEqual(patched.count(CALL), 1)
        self.assertIn(b"if ((MMC3_cmd & 0x07) < 6)", patched)
        self.assertIn(b'#include "../vpd_newppu_raw_step_probe.h"', patched)
        self.assertLess(patched.index(b"case 0x8001"), patched.index(CALL))
        self.assertLess(patched.index(CALL), patched.index(b"case 0xA000"))

    def test_crlf_source_line_endings_preserved(self):
        raw = MOCK.replace(b"\n", b"\r\n")
        patched = patch_mmc3(raw, require_pinned=False)
        self.assertEqual(patched.count(b"\r\n"), patched.count(b"\n"))

    def test_repeat_patching_rejected(self):
        once = patch_mmc3(MOCK, require_pinned=False)
        with self.assertRaisesRegex(ValueError, "already instrumented"):
            patch_mmc3(once, require_pinned=False)

    def test_missing_duplicated_or_moved_pinned_anchors_rejected(self):
        for raw in (
            MOCK.replace(b'#include "mapinc.h"', b"// no include"),
            MOCK.replace(b"DECLFW(MMC3_CMDWrite)", b"DECLFW(other)"),
            MOCK.replace(b"case 0x8001:", b"case 0xA001:"),
            MOCK.replace(b"\t\t\tpwrap(0xA000, V);", b"\t\t\tpwrap(0, V);"),
            MOCK + MOCK,
        ):
            with self.subTest(raw=raw[:45]), self.assertRaises(ValueError):
                patch_mmc3(raw, require_pinned=False)

    def test_mixed_line_endings_rejected(self):
        broken = MOCK.replace(b"\n", b"\r\n", 1)
        with self.assertRaisesRegex(ValueError, "Mixed"):
            patch_mmc3(broken, require_pinned=False)


class SyntheticMapper4Tests(unittest.TestCase):
    def test_mapper4_rom_with_32k_program_and_blank_chr(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "synthetic.nes"
            a = make_mapper4_chr_toggle_rom(p)
            raw = p.read_bytes()
            self.assertEqual(len(raw), 16 + 32768 + 16384)
            self.assertEqual(raw[:8], b"NES\x1a\x02\x02\x40\x00")
            self.assertEqual(raw[16:16 + len(PROGRAM)], PROGRAM)
            self.assertEqual(raw[16 + 16384:16 + 16384 + len(PROGRAM)], PROGRAM)
            self.assertEqual(raw[-16384:], bytes(16384))
            self.assertEqual(raw[16 + 32768 - 6:16 + 32768],
                             bytes((0, 0xc0)) * 3)
            self.assertEqual(a, make_mapper4_chr_toggle_rom(p))


class Mmc3ReportAcceptanceTests(unittest.TestCase):
    def test_accept_source_write_aggregate_but_not_chr_fetch_claim(self):
        p = verify_chr_write_report(MARKER)
        self.assertEqual(p["changed_chr_register_values"], 4095)
        self.assertFalse(p["chr_bank_to_pixel_causality_verified"])
        self.assertFalse(p["original_first_level_geometry_verified"])

    def test_refuse_missing_duplicate_or_hardware_claim(self):
        for s in (
            "", MARKER + "\n" + MARKER,
            MARKER.replace("chr_pixel_causality_proven=no",
                           "chr_pixel_causality_proven=yes"),
            MARKER.replace("writes=4096", "writes=128"),
        ):
            with self.subTest(s=s[:55]), self.assertRaises(Mmc3ProbeError):
                verify_chr_write_report(s)

    def test_refuse_bad_window_partition_or_no_actual_bank_changes(self):
        for old, new in (
            ("changed=4095", "changed=0"),
            ("within_source_window=960", "within_source_window=0"),
            ("outside_source_window=3136", "outside_source_window=3135"),
            ("after_cpu_high_read=800", "after_cpu_high_read=0"),
            ("after_cpu_high_read=800", "after_cpu_high_read=999"),
        ):
            with self.subTest(new=new), self.assertRaises(Mmc3ProbeError):
                verify_chr_write_report(MARKER.replace(old, new))

    def test_reject_inconsistent_ticks_and_invalid_counter(self):
        for old, new in (
            ("lag_min=1", "lag_min=100"),
            ("lag_max=70", "lag_max=1000001"),
            ("invalid=0", "invalid=1"),
        ):
            with self.subTest(new=new), self.assertRaises(Mmc3ProbeError):
                verify_chr_write_report(MARKER.replace(old, new))


@unittest.skipUnless(shutil.which("c++"), "C++ compiler not available")
class NativeMmc3CallbackTests(unittest.TestCase):
    def compile_run(self, enabled=True):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            p = folder / "mmc3.cpp"
            p.write_text(
                '#include "vpd_newppu_raw_step_probe.h"\n'
                '#include <cassert>\n'
                '#include <cstdlib>\n'
                'int main() {\n'
                f'  assert(setenv("VPD_STAGE106_MMC3_CHR_PROBE", "{1 if enabled else 0}", 1) == 0);\n'
                '  assert(setenv("VPD_STAGE104_EVENT_ORDER_PROBE", "1", 1) == 0);\n'
                '  for (int i = 0; i < 4096; ++i) {\n'
                '    if ((i % 256) == 0)\n'
                '      vpd_ppu_probe::event_order_assignment(true, true);\n'
                '    if ((i % 256) == 10)\n'
                '      vpd_ppu_probe::event_order_read(true, true, false);\n'
                '    if ((i % 256) == 60)\n'
                '      vpd_ppu_probe::event_order_assignment(false, false);\n'
                '    ++vpd_ppu_probe::channel().internal_tick_units;\n'
                '    vpd_ppu_probe::observe_native_mmc3_chr_write(2, i % 2);\n'
                '  }\n'
                '  return 0;\n'
                '}\n')
            binfile = folder / "mmc3"
            built = subprocess.run([
                "c++", "-std=c++11", "-Wall", "-Wextra", "-pedantic",
                "-Werror", "-DVPD_NATIVE_SYNTHETIC_EVENT_ORDER",
                "-DVPD_NATIVE_SYNTHETIC_MMC3_CHR",
                "-I", str(ROOT / "tools"), str(p), "-o", str(binfile),
            ], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            res = subprocess.run([str(binfile)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            return res.stderr

    def test_cxx11_mmc3_callback_produces_valid_aggregates(self):
        data = verify_chr_write_report(self.compile_run())
        self.assertGreater(data["writes_during_source_window"], 0)
        self.assertGreater(data["writes_after_high_cpu_read"], 0)

    def test_explicit_opt_out_emits_no_marker(self):
        self.assertNotIn("VPD_STAGE106_NATIVE_MMC3_CHR_PASS",
                         self.compile_run(enabled=False))


if __name__ == "__main__":
    unittest.main()
