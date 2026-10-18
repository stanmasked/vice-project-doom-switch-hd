"""Stage97 source hook site audit and native C++ candidate trace roundtrip."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_fceux_native_ppu_hook_sites import (
    FCEUX_REVISION, analyze_source, git_blob_sha,
)
from verify_native_ppu_raster_contract import audit_verified, FORMAT


def fake_source():
    return (
        "int newppu_get_scanline() { return ppur.status.sl; }\n"
        "int newppu_get_dot() { return ppur.status.cycle; }\n"
        "int FCEUPPU_Loop(int skip) {\n"
        "return FCEUX_PPU_Loop(skip);\n"
        "}\n"
        "int FCEUX_PPU_Loop(int skip) {\n"
        "ppur.status.sl = sl;\n"
        "const int yp = sl - 1;\n"
        "runppu(1);\n"
        "PPU_status |= 0x80;\n"
        "}\n"
    ).encode()


class SourceAnchorTests(unittest.TestCase):
    def test_known_shapes_not_mistaken_for_verified_engine(self):
        result = analyze_source(fake_source(), FCEUX_REVISION)
        self.assertFalse(result["upstream_blob_matches_pinned_source"])
        self.assertFalse(result["instrumentation_inserted_into_fceux"])
        self.assertFalse(result["safe_to_assume_native_counter_equals_nes_scanline"])
        self.assertTrue(result["newppu_and_legacy_paths_are_distinct"])

    def test_unpinned_revision_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown or unpinned"):
            analyze_source(fake_source(), "not-the-pinned-revision")

    def test_missing_getter_or_renderer_anchor_rejected(self):
        for fragment in (b"newppu_get_scanline", b"int FCEUX_PPU_Loop",
                         b"const int yp = sl - 1;", b"runppu(1);"):
            with self.subTest(fragment=fragment), self.assertRaisesRegex(
                    ValueError, "source anchor"):
                analyze_source(fake_source().replace(fragment, b"removed"), FCEUX_REVISION)

    def test_forged_unpinned_file_rejected_with_exact_sha(self):
        with self.assertRaisesRegex(ValueError, "pinned upstream"):
            analyze_source(fake_source(), FCEUX_REVISION, exact_pinned_source=True)

    def test_git_blob_digest_shape(self):
        content = b"example\n"
        expected = hashlib.sha1(b"blob 8\0example\n").hexdigest()
        self.assertEqual(git_blob_sha(content), expected)


@unittest.skipUnless(shutil.which("c++"), "C++ compiler not installed")
class NativeAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.temp.name) / "raster_smoke"
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([
            "c++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
            "-pedantic", "-I", str(root / "tools"),
            str(root / "tools/fceux_native_ppu_raster_adapter.cpp"),
            str(root / "tests/native_ppu_raster_adapter_smoke.cpp"),
            "-o", str(cls.binary),
        ], capture_output=True, text=True, check=False)
        if result.returncode:
            raise AssertionError(result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_native(self, mode):
        return subprocess.run([str(self.binary), mode],
                              capture_output=True, check=False)

    def test_adapter_emits_stage96_compatible_synthetic_trace(self):
        process = self.run_native("valid")
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "ppu_raster_events.tsv").write_bytes(process.stdout)
            manifest = {
                "format": FORMAT,
                "source_class": "synthetic_fixture",
                "engine_id": "fceux_candidate",
                "engine_revision": "0"*40,
                "timing_model": "ntsc_262_lines_341_dots",
                "native_hook_phase": "before_ppu_tick",
                "first_frame": 0,
                "frames_captured": 2,
                "events_recorded": 12,
                "events_sha256": hashlib.sha256(process.stdout).hexdigest(),
                "dropped_events": 0,
                "counter_discontinuities": 0,
                "capture_complete": True,
            }
            path = folder / "ppu_raster_manifest.json"
            path.write_text(json.dumps(manifest))
            audit = audit_verified(path)
            self.assertEqual(audit["events_accounted_for"], 12)
            self.assertFalse(audit["independent_native_fceux_origin_verified"])
            self.assertFalse(audit["actual_ppu_vblank_observation_verified"])

    def test_adapter_rejects_bad_native_event_sequences(self):
        for mode in ("duplicate_anchor", "missing_vblank", "out_of_bounds",
                     "bad_vblank"):
            with self.subTest(mode=mode):
                output = self.run_native(mode)
                self.assertNotEqual(output.returncode, 0, output.stdout)
                self.assertTrue(output.stderr)


if __name__ == "__main__":
    unittest.main()
