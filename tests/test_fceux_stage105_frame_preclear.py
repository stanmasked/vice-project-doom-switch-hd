"""Stage105 source pre-clear patch provenance and C++11/native report gates."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_fceux_newppu_probe_patch import patch_source
from inject_fceux_vblank_status_probe import add_boundary_hooks
from inject_fceux_ppustatus_read_probe import add_read_hook
from inject_fceux_frame_preclear_probe import insert_preclear, patch_checked
from run_stage105_native_frame_preclear import verify_preclear, PreclearError
import test_fceux_stage103_ppustatus_reads as fixtures

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = fixtures.SOURCE
MARKER = (
    "VPD_STAGE105_NATIVE_PRECLEAR_PASS reads=16384 "
    "sets=3 clears=2 pre_calls=2 high_reads=3 read_clears=3 "
    "low_after_high=500 pre_low_after_high=2 pre_high_after_high=0 "
    "pre_high_no_read=0 pre_low_no_read=0 "
    "high_to_pre_min=100 high_to_pre_max=200 invalid=0 "
    "source_only=yes hardware_vblank_proven=no"
)


def stage103_fixture(source=FIXTURE):
    return add_read_hook(add_boundary_hooks(patch_source(
        source, require_pinned=False)))


class FramePreclearContractTests(unittest.TestCase):
    def test_source_injection_is_strictly_pre_assignment(self):
        candidate = insert_preclear(stage103_fixture()).decode()
        before = candidate.index("preclear_before_assignment")
        assignment = candidate.index("\t\tPPU_status = 0;")
        after = candidate.index("observe_native_status_assignment(", assignment)
        self.assertLess(before, assignment)
        self.assertLess(assignment, after)
        self.assertEqual(candidate.count("preclear_before_assignment"), 1)

    def test_idempotent_injection_rejected(self):
        candidate = insert_preclear(stage103_fixture())
        with self.assertRaisesRegex(ValueError, "already instrumented"):
            insert_preclear(candidate)

    def test_wrong_source_context_rejected(self):
        fixture = stage103_fixture().replace(
            b"\t\tPPU_status = 0;", b"\t\tPPU_status = 0x00;")
        with self.assertRaisesRegex(ValueError, "Missing"):
            insert_preclear(fixture)

    def test_mixed_newlines_rejected(self):
        sample = stage103_fixture().replace(b"\n", b"\r\n", 1)
        with self.assertRaisesRegex(ValueError, "Mixed"):
            insert_preclear(sample)

    def test_original_line_endings_retained(self):
        candidate = insert_preclear(stage103_fixture(
            FIXTURE.replace(b"\n", b"\r\n")))
        self.assertEqual(candidate.count(b"\n"), candidate.count(b"\r\n"))

    def test_pinned_origin_required_for_full_patcher(self):
        with self.assertRaisesRegex(ValueError, "Unpinned"):
            patch_checked(FIXTURE, stage103_fixture())

    def test_accepts_source_only_aggregate(self):
        result = verify_preclear(MARKER)
        self.assertEqual(result["frame_clears_preceded_by_cpu_read"], 2)
        self.assertFalse(result["hardware_vblank_proven"])
        self.assertFalse(result["original_first_level_proven"])

    def test_missing_duplicate_and_forged_marker_rejected(self):
        for sample in (
            "none", MARKER + "\n" + MARKER,
            MARKER.replace("reads=16384", "reads=128"),
            MARKER.replace("source_only=yes", "source_only=no"),
            MARKER.replace("hardware_vblank_proven=no", "hardware_vblank_proven=yes"),
        ):
            with self.subTest(sample=sample[:40]), self.assertRaises(PreclearError):
                verify_preclear(sample)

    def test_mismatched_frame_preclear_categories_rejected(self):
        for from_text, to_text in (
            ("pre_calls=2", "pre_calls=1"),
            ("pre_low_after_high=2", "pre_low_after_high=0"),
            ("pre_low_after_high=2", "pre_low_after_high=1"),
            ("pre_high_after_high=0", "pre_high_after_high=1"),
            ("read_clears=3", "read_clears=2"),
            ("high_to_pre_min=100", "high_to_pre_min=300"),
            ("invalid=0", "invalid=1"),
        ):
            with self.subTest(replacement=to_text), self.assertRaises(PreclearError):
                verify_preclear(MARKER.replace(from_text, to_text))


@unittest.skipUnless(shutil.which("c++"), "C++ compiler unavailable")
class NativeFramePreclearHeaderTests(unittest.TestCase):
    def compile_run(self, enabled=True, corrupt=False):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            source = folder / "preclear.cpp"
            source.write_text(
                '#include "vpd_newppu_raw_step_probe.h"\n'
                '#include <cstdlib>\n'
                '#include <cassert>\n'
                'int main() {\n'
                f'  assert(setenv("VPD_STAGE105_PRECLEAR_PROBE", "{1 if enabled else 0}", 1) == 0);\n'
                '  vpd_ppu_probe::channel().internal_tick_units = 10;\n'
                '  vpd_ppu_probe::observe_native_status_assignment(true, true);\n'
                '  for (int i = 0; i < 16384; ++i) {\n'
                '    ++vpd_ppu_probe::channel().internal_tick_units;\n'
                '    if (i == 4096 || i == 12288) {\n'
                f'      vpd_ppu_probe::preclear_before_assignment({"true" if corrupt else "false"});\n'
                '      vpd_ppu_probe::observe_native_status_assignment(false, false);\n'
                '      vpd_ppu_probe::observe_native_status_assignment(true, true);\n'
                '    }\n'
                '    const bool high = (i == 100 || i == 4100 || i == 12300);\n'
                '    vpd_ppu_probe::observe_native_ppustatus_read(high, high, false);\n'
                '  }\n'
                '  return 0;\n'
                '}\n'
            )
            binary = folder / "preclear"
            result = subprocess.run([
                "c++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                "-pedantic", "-DVPD_NATIVE_SYNTHETIC_PRECLEAR",
                "-DVPD_NATIVE_SYNTHETIC_VBLANK",
                "-DVPD_NATIVE_SYNTHETIC_PPUSTATUS_READ",
                "-I", str(ROOT / "tools"), str(source), "-o", str(binary),
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            ran = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(ran.returncode, 0, ran.stderr)
            return ran.stderr

    def test_native_cxx11_preclear_categories_compiled(self):
        proof = verify_preclear(self.compile_run())
        self.assertEqual(proof["frame_clears_preceded_by_cpu_read"], 2)

    def test_explicit_opt_out_emits_no_evidence(self):
        self.assertNotIn("VPD_STAGE105_NATIVE_PRECLEAR_PASS",
                         self.compile_run(enabled=False))

    def test_invalid_preclear_bit_remains_fail_closed(self):
        with self.assertRaises(PreclearError):
            verify_preclear(self.compile_run(corrupt=True))


if __name__ == "__main__":
    unittest.main()
