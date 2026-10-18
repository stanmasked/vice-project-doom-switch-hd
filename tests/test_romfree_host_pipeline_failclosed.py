"""Fail-closed orchestration tests for the host runner.

Use fake cmake/ctest/auditor: these tests never pretend to compile a game.
The actual game-core and graphics-core builds remain separate CTests.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools"/"run_romfree_host_pipeline.sh"


@unittest.skipUnless(shutil.which("bash"), "bash is not installed")
class HostPipelineFailureInjection(unittest.TestCase):
    def test_real_shell_control_flow_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            (folder/"tools").mkdir()
            (folder/"game_core").mkdir()
            (folder/"graphics_core").mkdir()
            local=folder/"tools"/SCRIPT.name
            shutil.copyfile(SCRIPT,local)
            (folder/"tools"/"audit_romfree_combat_trace.py").write_text(
                'import os, sys\n'
                'print("FAKE_AUDIT_ONLY")\n'
                'sys.exit(int(os.environ.get("AUDIT_FAIL", "0")))\n',
                encoding="utf-8")
            cmake=folder/"fake_cmake.sh"
            cmake.write_text(
                '#!/usr/bin/env bash\n'
                'if [[ "$1" == "-S" ]]; then mkdir -p "$4"; fi\n'
                'exit 0\n',encoding="utf-8")
            ctest=folder/"fake_ctest.sh"
            ctest.write_text(
                '#!/usr/bin/env bash\n'
                'if [[ "$*" == *" -N" ]]; then\n'
                '  if [[ "$*" == *"graphics_core"* ]]; then\n'
                '    printf "scene_renderer_unit\\n'
                'game_to_graphics_integration\\n'
                'romfree_combat_to_raster_integration\\n"\n'
                '  else\n'
                '    printf "deterministic_simulation\\n'
                'romfree_combat_replay\\nromfree_combat_replay_csv\\n'
                'romfree_combat_replay_invalid\\n'
                'romfree_combat_full_trace\\n"\n'
                '    if [[ "${MISSING_TEST:-}" == "1" ]]; then\n'
                '      printf "romfree_combat_matrix_lookalike\\n"\n'
                '    else\n'
                '      printf "romfree_combat_matrix\\n"\n'
                '    fi\n'
                '  fi\n'
                'elif [[ "${CTEST_FAIL:-}" == "1" ]]; then\n'
                '  exit 1\n'
                'fi\nexit 0\n',encoding="utf-8")
            cmake.chmod(0o755)
            ctest.chmod(0o755)
            env={**os.environ,
                 "VPD_HOST_CMAKE":str(cmake),
                 "VPD_HOST_CTEST":str(ctest)}
            def check(args=(),changes=None):
                return subprocess.run(
                    ["bash",str(local),*args],
                    env={**env,**(changes or {})},
                    capture_output=True,text=True,timeout=15)
            ok_core=check(("--core-only",))
            self.assertEqual(ok_core.returncode,0,ok_core.stderr)
            self.assertIn("VPD_ROMFREE_HOST_PIPELINE_PASS scope=--core-only",
                          ok_core.stdout)
            ok_full=check()
            self.assertEqual(ok_full.returncode,0,ok_full.stderr)
            self.assertIn("VPD_ROMFREE_HOST_PIPELINE_PASS scope=all",
                          ok_full.stdout)
            for scenario,changed in (
                # A substring lookalike must never certify a missing test.
                ("missing_exact_name",{"MISSING_TEST":"1"}),
                ("ctest",{"CTEST_FAIL":"1"}),
                ("auditor",{"AUDIT_FAIL":"1"})
            ):
                with self.subTest(failure=scenario):
                    output=check(("--core-only",),changed)
                    self.assertNotEqual(output.returncode,0)
                    self.assertNotIn("VPD_ROMFREE_HOST_PIPELINE_PASS",
                                     output.stdout)
            invalid=check(("--invalid",))
            self.assertEqual(invalid.returncode,2)
            self.assertIn("Usage:",invalid.stderr)


if __name__=="__main__":
    unittest.main()
