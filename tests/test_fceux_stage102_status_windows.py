"""Stage102 exact FCEUX source anchors, native C++ status windows and audit."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_fceux_newppu_probe_patch import patch_source
from inject_fceux_vblank_status_probe import (
    add_boundary_hooks, patch_checked, ENTER, CLEAR,
)
from run_stage102_native_status_window import verify_window, WindowError


ROOT = Path(__file__).resolve().parents[1]
# Original, ROM-free fixture preserving the exact two source-level anchors.
SOURCE = (
    '#include "debug.h"\n'
    'void runppu(int x) {\n'
    '\tppur.status.cycle = (ppur.status.cycle + x) % ppur.status.end_cycle;\n'
    '\tif (!new_ppu_reset) X6502_Run(x);\n'
    '}\n'
    'int source_status_writes() {\n'
    '\t\tPPU_status |= 0x80;\n'
    '\t\tppuphase = PPUPHASE_VBL;\n'
    '\t\tPPU_status = 0;\n'
    '\t\t//this early out caused metroid to fail to boot.\n'
    '\t\treturn PPU_status;\n'
    '}\n'
).encode()
SAMPLE = ("VPD_STAGE102_NATIVE_STATUS_WINDOW_PASS entries=3 clears=3 "
          "entry_period_min=89200 entry_period_max=89342 "
          "entry_to_clear_min=6820 entry_to_clear_max=6821 "
          "invalid=0 hardware_vblank_proven=no raw_positions=no")


class PinnedSourceWindowTests(unittest.TestCase):
    def test_synthetic_stage98_then_stage102_injection_has_two_guarded_sites(self):
        stage98 = patch_source(SOURCE, require_pinned=False)
        output = add_boundary_hooks(stage98)
        self.assertEqual(output.count(b"observe_native_status_assignment"), 2)
        self.assertIn(b"true, (PPU_status & 0x80) != 0", output)
        self.assertIn(b"false, (PPU_status & 0x80) != 0", output)
        self.assertEqual(output.count(b"VPD_NATIVE_SYNTHETIC_VBLANK"), 2)

    def test_source_injection_preserves_original_crlf(self):
        stage98 = patch_source(SOURCE.replace(b"\n", b"\r\n"),
                               require_pinned=False)
        patched = add_boundary_hooks(stage98)
        self.assertEqual(patched.count(b"\n"), patched.count(b"\r\n"))

    def test_duplicate_or_missing_vblank_write_anchor_rejected(self):
        source = patch_source(SOURCE, require_pinned=False)
        for altered in (source.replace(ENTER, b"PPU_status|=0x80"),
                        source.replace(CLEAR, b"PPU_status=0"),
                        source + SOURCE[SOURCE.index(ENTER):],
                        source.replace(b"ppuphase = PPUPHASE_VBL;",
                                       b"ppuphase = 0;")):
            with self.subTest(altered=altered[:50]), self.assertRaisesRegex(
                    ValueError, "status-write anchors"):
                add_boundary_hooks(altered)

    def test_patch_cannot_install_twice(self):
        source = add_boundary_hooks(patch_source(SOURCE, require_pinned=False))
        with self.assertRaisesRegex(ValueError, "Already instrumented"):
            add_boundary_hooks(source)

    def test_source_must_be_exact_pinned_upstream_revision(self):
        with self.assertRaisesRegex(ValueError, "not the pinned blob"):
            patch_checked(SOURCE, patch_source(SOURCE, require_pinned=False))

    def test_wrong_patched_bytes_cannot_bypass_source_gate(self):
        with self.assertRaises(ValueError):
            patch_checked(SOURCE, SOURCE)

    def test_accept_valid_aggregate_no_hardware_claims(self):
        result = verify_window("boot\n" + SAMPLE + "\n")
        self.assertEqual(result["source_status_entries"], 3)
        self.assertEqual(result["min_entry_interval_internal_ticks"], 89200)
        self.assertFalse(result["nes_physical_vblank_proven"])

    def test_missing_duplicate_or_forged_status_window_rejected(self):
        for text in ("no status marker",
                     SAMPLE + "\n" + SAMPLE,
                     SAMPLE.replace("hardware_vblank_proven=no",
                                    "hardware_vblank_proven=yes"),
                     SAMPLE.replace("entries=3", "entries=2")):
            with self.subTest(text=text[:40]), self.assertRaises(WindowError):
                verify_window(text)

    def test_invalid_order_or_zero_period_rejected(self):
        changes = (
            ("invalid=0", "invalid=1"),
            ("entry_period_min=89200", "entry_period_min=0"),
            ("entry_period_max=89342", "entry_period_max=2"),
            ("entry_to_clear_max=6821", "entry_to_clear_max=90000"),
            ("entry_to_clear_min=6820", "entry_to_clear_min=0"),
        )
        for old, new in changes:
            with self.subTest(replacement=new), self.assertRaises(WindowError):
                verify_window(SAMPLE.replace(old, new))


@unittest.skipUnless(shutil.which("c++"), "C++ compiler unavailable")
class NativeStatusWindowCppTests(unittest.TestCase):
    def test_cxx11_compiled_status_window_emits_three_pairs(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            source = temp / "status.cpp"
            source.write_text(
                '#include "vpd_newppu_raw_step_probe.h"\n'
                '#include <cassert>\n'
                '#include <cstdlib>\n'
                'int main() {\n'
                '  assert(setenv("VPD_STAGE102_STATUS_PROBE", "1", 1) == 0);\n'
                '  for (int i = 0; i < 3; ++i) {\n'
                '    vpd_ppu_probe::channel().internal_tick_units += 1000;\n'
                '    vpd_ppu_probe::observe_native_status_assignment(true, true);\n'
                '    vpd_ppu_probe::channel().internal_tick_units += 400;\n'
                '    vpd_ppu_probe::observe_native_status_assignment(false, false);\n'
                '  }\n'
                '  return 0;\n'
                '}\n')
            binary = temp / "status"
            cmd = ["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                   "-pedantic", "-DVPD_NATIVE_SYNTHETIC_VBLANK",
                   "-I", str(ROOT / "tools"), str(source), "-o", str(binary)]
            compiled = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            ran = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(ran.returncode, 0, ran.stderr)
            proof = verify_window(ran.stderr)
            self.assertEqual(proof["min_entry_interval_internal_ticks"], 1400)
            self.assertEqual(proof["min_entry_to_clear_internal_ticks"], 400)


if __name__ == "__main__":
    unittest.main()
