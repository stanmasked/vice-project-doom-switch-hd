"""Stage96 native PPU trace contract and no-ROM checksum regressions."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from make_synthetic_ppu_raster_trace import synthetic_capture
from verify_native_ppu_raster_contract import (
    audit_verified, validate_manifest, RasterContractError,
)


class PpuRasterContractTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = synthetic_capture(temp.name)
        self.log = self.path.parent / "ppu_raster_events.tsv"

    def set_manifest(self, **updates):
        manifest = json.loads(self.path.read_text())
        manifest.update(updates)
        self.path.write_text(json.dumps(manifest)+"\n")

    def change(self, old, new, *, correct_digest=True):
        contents = self.log.read_bytes()
        self.assertIn(old, contents)
        contents = contents.replace(old, new)
        self.log.write_bytes(contents)
        if correct_digest:
            self.set_manifest(events_sha256=hashlib.sha256(contents).hexdigest())

    def test_valid_synthetic_frames_have_only_structural_evidence(self):
        r = audit_verified(self.path)
        self.assertEqual(r["frames_accounted_for"], 2)
        self.assertEqual(r["events_accounted_for"], 12)
        self.assertEqual(r["aggregate_event_types"]["vblank_enter"], 2)
        self.assertTrue(r["event_stream_sha256_verified"])
        self.assertFalse(r["independent_native_fceux_origin_verified"])
        self.assertFalse(r["actual_ppu_vblank_observation_verified"])
        self.assertEqual(r["hd_background_cells_ready"], 0)

    def test_more_synthetic_frames_and_nonzero_origin(self):
        r = audit_verified(synthetic_capture(self.path.parent, frames=3,
                                               first_frame=10))
        self.assertEqual(r["events_accounted_for"], 18)
        self.assertEqual(r["frames_accounted_for"], 3)

    def test_claimed_native_source_does_not_make_trusted(self):
        self.set_manifest(source_class="candidate_native_unverified",
                          engine_revision="f"*40)
        r = audit_verified(self.path)
        self.assertFalse(r["independent_native_fceux_origin_verified"])
        self.assertFalse(r["cpu_to_raster_visibility_verified"])

    def test_corrupt_checksum_rejected(self):
        self.change(b"60\t48", b"60\t49", correct_digest=False)
        with self.assertRaisesRegex(RasterContractError, "checksum mismatch"):
            audit_verified(self.path)

    def test_rehashed_wrong_vblank_start_rejected(self):
        self.change(b"241\t1\tvblank_enter", b"241\t2\tvblank_enter")
        with self.assertRaisesRegex(RasterContractError, "VBlank start"):
            audit_verified(self.path)

    def test_rehashed_wrong_vblank_end_rejected(self):
        self.change(b"261\t1\tvblank_exit", b"261\t2\tvblank_exit")
        with self.assertRaisesRegex(RasterContractError, "VBlank end"):
            audit_verified(self.path)

    def test_duplicate_anchor_rejected(self):
        self.change(b"10\t12\tpixel_fetch_sample", b"0\t0\tframe_anchor")
        with self.assertRaisesRegex(RasterContractError, "anchor"):
            audit_verified(self.path)

    def test_order_regression_rejected(self):
        self.change(b"130\t12\tscroll_context", b"59\t12\tscroll_context")
        with self.assertRaisesRegex(RasterContractError, "Nonmonotonic"):
            audit_verified(self.path)

    def test_discontinuous_frame_labels_rejected(self):
        self.change(b"\n1\t", b"\n3\t")
        with self.assertRaisesRegex(RasterContractError, "Nonconsecutive"):
            audit_verified(self.path)

    def test_pixel_sample_must_be_visible(self):
        self.change(b"10\t12\tpixel_fetch_sample", b"0\t0\tpixel_fetch_sample")
        with self.assertRaisesRegex(RasterContractError, "visible area"):
            audit_verified(self.path)

    def test_invalid_kind_rejected(self):
        self.change(b"scroll_context", b"chr_data_bytes")
        with self.assertRaisesRegex(RasterContractError, "event kind"):
            audit_verified(self.path)

    def test_missing_newline_rejected_even_after_rehash(self):
        payload = self.log.read_bytes()[:-1]
        self.log.write_bytes(payload)
        self.set_manifest(events_sha256=hashlib.sha256(payload).hexdigest())
        with self.assertRaisesRegex(RasterContractError, "Truncated"):
            audit_verified(self.path)

    def test_extra_column_rejected(self):
        self.change(b"frame\tscanline\tdot\tkind\n",
                    b"frame\tscanline\tdot\tkind\tbank\n")
        with self.assertRaisesRegex(RasterContractError, "header"):
            audit_verified(self.path)

    def test_unfinished_and_lost_event_reports_rejected(self):
        for flag in ("dropped_events", "counter_discontinuities"):
            with self.subTest(flag=flag):
                self.set_manifest(**{flag: 1})
                with self.assertRaises(RasterContractError):
                    audit_verified(self.path)
                self.set_manifest(**{flag: 0})
        self.set_manifest(capture_complete=False)
        with self.assertRaisesRegex(RasterContractError, "Unfinished"):
            audit_verified(self.path)

    def test_unrecognized_schema_field_rejected(self):
        data = json.loads(self.path.read_text())
        data["pixel_bytes"] = "not allowed"
        with self.assertRaisesRegex(RasterContractError, "manifest fields"):
            validate_manifest(json.dumps(data))

    def test_wrong_timing_model_or_phase_rejected(self):
        self.set_manifest(timing_model="pal")
        with self.assertRaisesRegex(RasterContractError, "timing model"):
            audit_verified(self.path)
        self.set_manifest(timing_model="ntsc_262_lines_341_dots",
                          native_hook_phase="unspecified")
        with self.assertRaisesRegex(RasterContractError, "hook phase"):
            audit_verified(self.path)

    def test_numeric_string_and_bad_digest_rejected(self):
        self.set_manifest(first_frame="0")
        with self.assertRaisesRegex(RasterContractError, "Invalid number"):
            audit_verified(self.path)
        self.set_manifest(first_frame=0, events_sha256="f"*63)
        with self.assertRaisesRegex(RasterContractError, "SHA256"):
            audit_verified(self.path)

    def test_summary_cannot_export_screen_positions_or_original_data(self):
        report = json.dumps(audit_verified(self.path))
        for forbidden in ('"scanline":', '"dot":', "chr_register_value",
                          "raw_ppu_bytes", "original_rom_sha256"):
            self.assertNotIn(forbidden, report)


if __name__ == "__main__":
    unittest.main()
