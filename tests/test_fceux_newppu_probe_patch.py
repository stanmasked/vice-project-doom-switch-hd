"""Stage98 opt-in raw newppu hook injection and real C++ compile checks."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_fceux_newppu_probe_patch import (
    OPEN, STEP, patch_source, create_candidate,
)

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "tools" / "vpd_newppu_raw_step_probe.h"
STUB = (
    '#include "debug.h"\n'
    'void runppu(int x) {\n'
    '\tppur.status.cycle = (ppur.status.cycle + x) % ppur.status.end_cycle;\n'
    '\tif (!new_ppu_reset) X6502_Run(x);\n'
    '}\n'
).encode()


class PatchSourceTests(unittest.TestCase):
    def test_default_requires_real_pinned_upstream_sha(self):
        with self.assertRaisesRegex(ValueError, "Unpinned"):
            patch_source(STUB)

    def test_synthetic_anchor_receives_gated_raw_before_after_hook(self):
        patch = patch_source(STUB, require_pinned=False).decode()
        self.assertEqual(patch.count("#ifdef VPD_NATIVE_RAW_PPU_PROBE"), 3)
        self.assertEqual(patch.count("vpd_ppu_probe::observe("), 1)
        self.assertIn("const int vpd_cycle_before = ppur.status.cycle", patch)
        self.assertIn("const int vpd_end_cycle = ppur.status.end_cycle", patch)
        self.assertIn("#include \"vpd_newppu_raw_step_probe.h\"", patch)

    def test_CRLF_is_preserved_for_original_source_shape(self):
        data = STUB.replace(b"\n", b"\r\n")
        result = patch_source(data, require_pinned=False)
        self.assertEqual(result.count(b"\n"), result.count(b"\r\n"))
        self.assertIn(b"\r\n#ifdef VPD_NATIVE_RAW_PPU_PROBE\r\n", result)

    def test_duplicate_missing_modified_hook_point_fail_closed(self):
        for corrupt in (
            STUB + STUB,
            STUB.replace(STEP, b"\tppur.status.cycle += x;"),
            STUB.replace(OPEN, b"void incorrect(int x) {"),
            STUB.replace(b'#include "debug.h"', b'// no include'),
        ):
            with self.subTest(content=corrupt), self.assertRaises(ValueError):
                patch_source(corrupt, require_pinned=False)

    def test_avoid_double_instrumentation(self):
        once = patch_source(STUB, require_pinned=False)
        with self.assertRaisesRegex(ValueError, "probe"):
            patch_source(once, require_pinned=False)

    def test_real_checkout_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            src = Path(temp) / "src"
            src.mkdir()
            path = src / "ppu.cpp"
            path.write_bytes(STUB)
            with self.assertRaisesRegex(ValueError, "rewrite"):
                create_candidate(path, temp, HEADER)


@unittest.skipUnless(shutil.which("c++"), "C++ compiler unavailable")
class CompiledHookTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "debug.h").write_text("// mock FCEUX include\n")
        (self.root / "vpd_newppu_raw_step_probe.h").write_bytes(
            HEADER.read_bytes())
        before = (
            "#include <cassert>\n"
            "struct Status {int sl; int cycle; int end_cycle;};\n"
            "struct Core {Status status;};\n"
            "Core ppur = {{42, 339, 341}};\n"
            "bool new_ppu_reset = false;\n"
            "int cpu_advance = 0;\n"
            "void X6502_Run(int x) { cpu_advance += x; }\n"
        )
        tail = (
            "#ifdef VPD_NATIVE_RAW_PPU_PROBE\n"
            "int calls = 0;\n"
            "void sink(const vpd_ppu_probe::RawStep& s, void*) {\n"
            "  assert(s.internal_scanline == 42);\n"
            "  assert(s.cycle_modulus == 341);\n"
            "  if (calls == 0) {assert(s.cycle_before == 339 && s.cycle_after == 340);}\n"
            "  if (calls == 1) {assert(s.cycle_before == 340 && s.cycle_after == 1);}\n"
            "  ++calls;\n"
            "}\n"
            "#endif\n"
            "int main() {\n"
            "#ifdef VPD_NATIVE_RAW_PPU_PROBE\n"
            "  vpd_ppu_probe::set_sink(sink, nullptr);\n"
            "#endif\n"
            "  runppu(1); runppu(2);\n"
            "  assert(ppur.status.cycle == 1);\n"
            "  assert(cpu_advance == 3);\n"
            "#ifdef VPD_NATIVE_RAW_PPU_PROBE\n"
            "  assert(calls == 2);\n"
            "  assert(vpd_ppu_probe::channel().observed == 2);\n"
            "  assert(vpd_ppu_probe::channel().invalid == 0);\n"
            "#endif\n"
            "  return 0;\n"
            "}\n"
        )
        self.source = self.root / "synthetic.cpp"
        self.source.write_text(
            before + patch_source(STUB, require_pinned=False).decode() + tail)

    def compile_and_run(self, enabled):
        binary = self.root / ("enabled" if enabled else "disabled")
        command = ["c++", "-std=c++11", "-Wall", "-Wextra",
                   "-Werror", "-pedantic", "-I", str(self.root)]
        if enabled:
            command.append("-DVPD_NATIVE_RAW_PPU_PROBE")
        command.extend([str(self.source), "-o", str(binary)])
        compilation = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(compilation.returncode, 0, compilation.stderr)
        outcome = subprocess.run([str(binary)], capture_output=True, text=True)
        self.assertEqual(outcome.returncode, 0, outcome.stderr)

    def test_disabled_original_update_path_unchanged(self):
        self.compile_and_run(False)

    def test_opt_in_probe_observes_raw_values_without_mapping(self):
        self.compile_and_run(True)


if __name__ == "__main__":
    unittest.main()
