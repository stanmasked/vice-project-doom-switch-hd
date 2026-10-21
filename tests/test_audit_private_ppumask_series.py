"""Synthetic-only four-case PPUMASK raster and CPU phase provenance tests."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_private_ppumask_series import audit_series
from test_audit_private_ppumask_ab import make_fixture


FRAMES = (600, 700, 800, 900)


def series_fixture(root, *, changed=None, palette_off=None, change_row=None):
    data = []
    for frame in FRAMES:
        folder = root / f"case_{frame}"
        folder.mkdir()
        args = dict(target=frame, change_at=frame + 1,
                    palette_mutation=(frame != palette_off))
        if frame == changed:
            args["change_at"] = frame + 2
        if frame == change_row:
            args["y"] = 220
        original, probe = make_fixture(folder, **args)
        data.append(dict(frame=frame, original_dir=str(original), probe_dir=str(probe)))
    manifest = root / "invented_manifest.json"
    manifest.write_text(json.dumps(data), encoding="utf8")
    return manifest


def clocks(root, *, broken=False):
    anchors = root / "invented_clock.tsv"
    anchor_witness = root / "invented_clock_complete.txt"
    instructions = root / "invented_exec.tsv"
    exec_witness = root / "invented_exec_complete.txt"
    times = {}
    rows = []
    for i, frame in enumerate(FRAMES):
        previous = (frame - 599) * 29781
        current = previous + 29781
        if broken and frame == 800:
            current = previous + 20000
        times[frame] = previous
        rows.extend([(frame - 1, previous), (frame, current)])
    with anchors.open("w", encoding="ascii", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["frame", "cycle"])
        writer.writerows(rows)
    anchor_witness.write_text(
        "format=private_original_fceux_frame_anchor_v1\n"
        "first_observed_frame=1\n"
        "last_observed_frame=900\n"
        "frame_gaps=0\nrom_identity_verified=yes\nmovie_readonly_verified=yes\n",
        encoding="ascii")
    with instructions.open("w", encoding="ascii", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["frame", "cycle", "type", "address",
                         "value", "a", "x", "y", "p"])
        for i, frame in enumerate(FRAMES):
            writer.writerow([frame, times[frame] + 24332 + (i % 2),
                             "PC", "E38E", "00", "0E", "00", "00", "24"])
    exec_witness.write_text(
        "format=private_stage155_cpu_sequence_v1\n"
        "first_observed_frame=1\n"
        "last_observed_frame=900\n"
        "frame_gaps=0\nrom_identity_verified=yes\nmovie_readonly_verified=yes\n",
        encoding="ascii")
    return (anchors, anchor_witness, instructions, exec_witness)


class PPUMASKSeriesTests(unittest.TestCase):
    def test_four_independent_cases_share_exact_row_set(self):
        with tempfile.TemporaryDirectory() as d:
            manifest = series_fixture(Path(d))
            report = audit_series(manifest)
            self.assertEqual(report["case_count"], 4)
            self.assertEqual(report["shared_affected_row_indices"], [202])
            self.assertTrue(report["rgb_pal_pixel_masks_identical_in_every_case"])
            self.assertTrue(report["all_cpu_accumulator_restoration_explicitly_witnessed"])
            self.assertFalse(report["absolute_cpu_instruction_scanline_proven"])
            self.assertFalse(report["cross_run_cpu_cycle_phase_observed"])
            self.assertNotIn(str(d), json.dumps(report))

    def test_private_phase_is_cross_run_relative_not_scanline_proof(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            report = audit_series(series_fixture(root), **dict(zip(
                ("anchor_tsv", "anchor_witness", "cpu_tsv", "cpu_witness"),
                clocks(root))))
            self.assertTrue(report["cross_run_cpu_cycle_phase_observed"])
            self.assertEqual(report["cpu_e38e_phase_min_cycles"], 24332)
            self.assertEqual(report["cpu_e38e_phase_max_cycles"], 24333)
            self.assertEqual(report["cpu_e38e_phase_spread_cycles"], 1)
            self.assertFalse(report["independent_ppu_dot_origin_calibration"])

    def test_missing_palette_difference_position_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "spatial change masks disagree"):
                audit_series(series_fixture(Path(d), palette_off=700))

    def test_different_changed_row_set_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "different visible affected-row"):
                audit_series(series_fixture(Path(d), change_row=900))

    def test_wrong_frame_response_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "next captured frame"):
                audit_series(series_fixture(Path(d), changed=700))

    def test_missing_restoration_witness_does_not_claim_restoration(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = series_fixture(root)
            probe_marker = root / "case_600" / "probe" / "COMPLETE.txt"
            probe_marker.write_text("".join(line for line in
                probe_marker.read_text("ascii").splitlines(True)
                if not line.startswith("accumulator_restored_before_rts=")), "ascii")
            result = audit_series(manifest)
            self.assertFalse(result["all_cpu_accumulator_restoration_explicitly_witnessed"])

    def test_bad_frame_clock_epoch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = series_fixture(root)
            paths = clocks(root, broken=True)
            with self.assertRaisesRegex(ValueError, "CPU cycle clock epochs"):
                audit_series(manifest, **dict(zip(
                    ("anchor_tsv", "anchor_witness", "cpu_tsv", "cpu_witness"), paths)))

    def test_partial_cpu_provenance_arguments_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = series_fixture(root)
            with self.assertRaisesRegex(ValueError, "all four private CPU"):
                audit_series(manifest, anchor_tsv=clocks(root)[0])

    def test_reused_capture_directory_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = series_fixture(root)
            rows = json.loads(manifest.read_text("utf8"))
            rows[1]["original_dir"] = rows[0]["original_dir"]
            manifest.write_text(json.dumps(rows), encoding="utf8")
            with self.assertRaisesRegex(ValueError, "directory reused"):
                audit_series(manifest)

    def test_unsorted_duplicate_target_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = series_fixture(root)
            rows = json.loads(manifest.read_text("utf8"))
            rows[2]["frame"] = 700
            manifest.write_text(json.dumps(rows), encoding="utf8")
            with self.assertRaisesRegex(ValueError, "sorted and distinct"):
                audit_series(manifest)


if __name__ == "__main__":
    unittest.main()
