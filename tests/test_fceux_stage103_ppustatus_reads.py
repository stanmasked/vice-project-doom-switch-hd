"""Stage103 $2002 handler instrumentation, NROM poll and fail-closed tests."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_fceux_newppu_probe_patch import patch_source
from inject_fceux_vblank_status_probe import add_boundary_hooks
from inject_fceux_ppustatus_read_probe import (
    add_read_hook, patch_checked, BEFORE, CLEAR, GUARD,
)
from make_stage103_ppustatus_poll_rom import make_ppustatus_poll_rom
from run_stage103_native_ppustatus_reads import (
    verify_read_marker, ReadProbeError,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    '#include "debug.h"\n'
    'void runppu(int x) {\n'
    '\tppur.status.cycle = (ppur.status.cycle + x) % ppur.status.end_cycle;\n'
    '\tif (!new_ppu_reset) X6502_Run(x);\n'
    '}\n'
    'static DECLFR(A2002) {\n'
    '\tuint8 ret = PPU_status;\n'
    '\t{\n'
    '\t\tvtoggle = 0;\n'
    '\t\tPPU_status &= 0x7F;\n'
    '\t\tPPUGenLatch = ret;\n'
    '\t}\n'
    '\treturn ret;\n'
    '}\n'
    'static DECLFR(A2004) {\n'
    '\treturn 0;\n'
    '}\n'
    'int FCEUX_PPU_Loop(int skip) {\n'
    '\t\tPPU_status |= 0x80;\n'
    '\t\tppuphase = PPUPHASE_VBL;\n'
    '\t\tPPU_status = 0;\n'
    '\t\t//this early out caused metroid to fail to boot.\n'
    '\t\treturn 0;\n'
    '}\n'
).encode()
MARKER = ("VPD_STAGE103_NATIVE_PPUSTATUS_READ_PASS reads=16384 "
          "returned_high=6 before_high=6 cleared_high=6 "
          "after_high=0 invalid=0 source_only=yes hardware_vblank_proven=no")


class SourceReadHookTests(unittest.TestCase):
    def fixture(self, source=SOURCE):
        return add_boundary_hooks(patch_source(source, require_pinned=False))

    def test_pinned_handler_inserted_once_only_on_read_clear(self):
        patched = add_read_hook(self.fixture())
        self.assertEqual(patched.count(GUARD), 2)
        self.assertEqual(patched.count(b"observe_native_ppustatus_read"), 1)
        self.assertIn(b"if (newppu)", patched)
        self.assertIn(BEFORE, patched)
        self.assertIn(CLEAR, patched)
        self.assertIn(b"vpd_2002_before", patched)
        self.assertIn(b"(ret & 0x80) != 0", patched)

    def test_crlf_preserved(self):
        patched = add_read_hook(self.fixture(SOURCE.replace(b"\n", b"\r\n")))
        self.assertEqual(patched.count(b"\n"), patched.count(b"\r\n"))

    def test_duplicate_instrumentation_is_refused(self):
        once = add_read_hook(self.fixture())
        with self.assertRaisesRegex(ValueError, "Already instrumented"):
            add_read_hook(once)

    def test_unexpected_handler_or_clear_location_refused(self):
        for bad in (
            SOURCE.replace(b"static DECLFR(A2002) {", b"static unrelated() {"),
            SOURCE.replace(b"static DECLFR(A2004) {", b"static unrelated() {"),
            SOURCE.replace(CLEAR, b"PPU_status = 0;"),
            SOURCE + b"static DECLFR(A2002) {\n}\n",
            SOURCE.replace(b"PPUGenLatch = ret;", b"PPUGenLatch = 1;"),
        ):
            with self.subTest(bad=bad[:32]), self.assertRaises(ValueError):
                add_read_hook(self.fixture(bad))

    def test_unpinned_source_cannot_bypass_patch_chain(self):
        with self.assertRaisesRegex(ValueError, "Unpinned"):
            patch_checked(SOURCE, self.fixture())

    def test_synthetic_rom_has_no_original_asset_bytes(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "poll.nes"
            checksum = make_ppustatus_poll_rom(path)
            blob = path.read_bytes()
            self.assertEqual(blob[:6], b"NES\x1a\x01\x01")
            self.assertEqual(blob[16:22], bytes((0xAD, 2, 0x20, 0x4C, 0, 0xC0)))
            self.assertEqual(blob[-8192:], bytes(8192))
            self.assertEqual(len(blob), 24592)
            self.assertEqual(make_ppustatus_poll_rom(path), checksum)

    def test_valid_marker_does_not_claim_physical_vblank(self):
        proof = verify_read_marker(MARKER)
        self.assertEqual(proof["synthetic_cpu_reads"], 16384)
        self.assertEqual(proof["source_high_cleared"], 6)
        self.assertFalse(proof["physical_nes_vblank_proven"])

    def test_missing_duplicate_unrecognized_marker_refused(self):
        for marker in (
            "nothing",
            MARKER + "\n" + MARKER,
            MARKER.replace("source_only=yes", "source_only=no"),
            MARKER.replace("reads=16384", "reads=4096"),
            MARKER.replace("hardware_vblank_proven=no",
                           "hardware_vblank_proven=yes"),
        ):
            with self.subTest(marker=marker[:32]), self.assertRaises(
                    ReadProbeError):
                verify_read_marker(marker)

    def test_mismatched_read_return_or_uncleared_bit_refused(self):
        for old, new in (
            ("returned_high=6", "returned_high=5"),
            ("before_high=6", "before_high=0"),
            ("cleared_high=6", "cleared_high=3"),
            ("after_high=0", "after_high=1"),
            ("invalid=0", "invalid=1"),
        ):
            with self.subTest(new=new), self.assertRaises(ReadProbeError):
                verify_read_marker(MARKER.replace(old, new))


@unittest.skipUnless(shutil.which("c++"), "C++ compiler unavailable")
class CompiledReadCallbackTests(unittest.TestCase):
    def test_real_cxx11_source_callback_reports_only_aggregates(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            source = directory / "read.cpp"
            source.write_text(
                '#include "vpd_newppu_raw_step_probe.h"\n'
                '#include <cstdlib>\n'
                '#include <cassert>\n'
                'int main() {\n'
                '  assert(setenv("VPD_STAGE103_PPUSTATUS_READ_PROBE", "1", 1) == 0);\n'
                '  for (int i = 0; i < 16384; ++i) {\n'
                '    bool high = (i % 2048 == 0);\n'
                '    vpd_ppu_probe::observe_native_ppustatus_read(high, high, false);\n'
                '  }\n'
                '  return 0;\n'
                '}\n')
            binary = directory / "read"
            compiler = subprocess.run([
                "c++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                "-pedantic", "-DVPD_NATIVE_SYNTHETIC_PPUSTATUS_READ",
                "-I", str(ROOT / "tools"), str(source), "-o", str(binary),
            ], capture_output=True, text=True)
            self.assertEqual(compiler.returncode, 0, compiler.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            proof = verify_read_marker(result.stderr)
            self.assertEqual(proof["source_high_cleared"], 8)


if __name__ == "__main__":
    unittest.main()
