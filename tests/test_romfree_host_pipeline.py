"""Static safety checks for the portable ROM-free host test launcher.

These checks don't replace actually running CMake, CTest, or the raster tests.
"""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools"/"run_romfree_host_pipeline.sh"


class HostPipelineScriptTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("bash"), "bash is unavailable")
    def test_shell_syntax_and_rejected_arguments(self):
        syntax=subprocess.run(["bash", "-n", str(SCRIPT)],
                              capture_output=True, text=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        bad=subprocess.run(["bash", str(SCRIPT), "--unknown"],
                           capture_output=True, text=True, timeout=8)
        self.assertEqual(bad.returncode, 2)
        self.assertIn("Usage:", bad.stderr)
        too_many=subprocess.run(["bash", str(SCRIPT), "--core-only", "extra"],
                                capture_output=True, text=True, timeout=8)
        self.assertEqual(too_many.returncode, 2)

    def test_hard_fail_and_no_forged_success_without_every_test(self):
        source=SCRIPT.read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", source)
        self.assertIn("require_ctest", source)
        self.assertIn('"$ctest_cmd" --test-dir "$build_root/game_core"', source)
        self.assertIn('"$ctest_cmd" --test-dir "$build_root/graphics_core"', source)
        self.assertIn("romfree_combat_matrix", source)
        self.assertIn("romfree_combat_full_trace", source)
        self.assertIn("romfree_combat_to_raster_integration", source)
        self.assertIn("tools/audit_romfree_combat_trace.py", source)
        self.assertIn("VPD_ROMFREE_HOST_PIPELINE_PASS", source)
        self.assertIn("switch_runtime_proven=no", source)
        self.assertIn("original_game_proven=no", source)
        self.assertNotIn("curl ", source)
        self.assertNotIn("wget ", source)
        self.assertNotIn(".nes", source.lower())


if __name__=="__main__":
    unittest.main()
