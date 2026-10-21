"""All data generated below are invented; original movie frames are anchors only."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_private_road_ppu_alignment import ANCHORS
from audit_private_road_ppu_window import (
    MOVIE_FRAMES, CPU_FRAMES, PUBLISHED_IMAGE, validate_complete_window
)

# Arbitrary synthetic rejected-slot selection. NOT actual four rejected frames.
SYNTHETIC_REJECTED = {608, 616, 624, 632}


def fixture():
    road = {
        "schema": "road_image_cross_sections_window_v1",
        "rom_sha256": "a" * 64,
        "fm2_sha256": "b" * 64,
        "movie_frame_origin": "zero_based_FM2",
        "slots": [],
    }
    ppu = {
        "schema": "ppu_cpu_writer_phases_v1",
        "rom_sha256": "a" * 64,
        "fm2_sha256": "b" * 64,
        "movie_frame_origin": "zero_based_FM2",
        "samples": [],
    }
    for frame in MOVIE_FRAMES:
        if frame in SYNTHETIC_REJECTED:
            road["slots"].append({"frame": frame, "status": "ambiguous"})
        else:
            left, right = PUBLISHED_IMAGE.get(frame, (60, 190))
            road["slots"].append({
                "frame": frame, "status": "accepted",
                "left": left, "right": right,
            })
    for frame in CPU_FRAMES:
        original = ANCHORS.get(frame)
        second = original[2] if original else (frame % 200) + 10
        post = original[3] if original else (frame % 200) + 9
        ppu["samples"].append({
            "frame": frame,
            "writer_pcs": ["E8EC", "E8F1", "E369", "E36C"],
            "written_values": [0, second, 0, 0],
            "cpu_cycles_after_previous_frame": [1000, 1007, 24286, 24290],
            "ram_0d_postframe": post,
        })
    return road, ppu


class CompleteWindowAuditTests(unittest.TestCase):
    def assert_rejects(self, modify):
        road, ppu = fixture()
        modify(road, ppu)
        with self.assertRaises(ValueError):
            validate_complete_window(road, ppu)

    def test_full_synthetic_window_passes(self):
        road, ppu = fixture()
        data = validate_complete_window(road, ppu)
        self.assertEqual(data["cpu_frames_checked"], 321)
        self.assertEqual(data["road_slots_checked"], 41)
        self.assertEqual(data["road_cross_sections_accepted"], 37)
        self.assertEqual(data["road_slots_ambiguous"], 4)
        self.assertEqual(data["source_ppu_writes_checked"], 1284)
        self.assertFalse(data["camera_speed_proven"])
        self.assertNotIn("rom_sha256", data)
        self.assertNotIn("rejected_frames", data)

    def test_missing_rgb_frame_rejected(self):
        self.assert_rejects(lambda a,b: a["slots"].pop(6))

    def test_duplicate_rgb_frame_rejected(self):
        self.assert_rejects(lambda a,b: a["slots"].__setitem__(
            5, copy.deepcopy(a["slots"][4])))

    def test_rejected_frame_must_not_have_invented_width(self):
        self.assert_rejects(lambda a,b: a["slots"][1].update(left=66))

    def test_ambiguous_count_wrong(self):
        self.assert_rejects(lambda a,b: a["slots"][1].update(
            status="accepted",left=63,right=190))

    def test_documented_road_frame_must_be_accepted(self):
        self.assert_rejects(lambda a,b: a["slots"][0].clear())

    def test_documented_road_edge_must_match(self):
        self.assert_rejects(lambda a,b: a["slots"][20].update(left=99))

    def test_wrong_movie_identity(self):
        self.assert_rejects(lambda a,b: b.update(fm2_sha256="c"*64))

    def test_wrong_rom_identity(self):
        self.assert_rejects(lambda a,b: b.update(rom_sha256="c"*64))

    def test_missing_cpu_frame_rejected(self):
        self.assert_rejects(lambda a,b: b["samples"].pop(250))

    def test_reordered_cpu_frame_rejected(self):
        self.assert_rejects(lambda a,b: b["samples"].__setitem__(
            100,copy.deepcopy(b["samples"][99])))

    def test_late_ppu_writer_provenance_mutated(self):
        self.assert_rejects(lambda a,b: b["samples"][99]["writer_pcs"].__setitem__(2,"E368"))

    def test_cpu_cycle_phase_mutated(self):
        self.assert_rejects(lambda a,b: b["samples"][120][
            "cpu_cycles_after_previous_frame"].__setitem__(3,24292))

    def test_cpu_second_ppu_value_mutated(self):
        self.assert_rejects(lambda a,b: b["samples"][144][
            "written_values"].__setitem__(1,137))

    def test_unexpected_original_media_path_field_rejected(self):
        self.assert_rejects(lambda a,b: a.update(
            private_png_path="/home/owner/nes_capture.png"))

    def test_road_source_must_be_same_movie_frame_origin(self):
        self.assert_rejects(lambda a,b: a.update(movie_frame_origin="one_based"))

    def test_noninteger_cpu_frame_rejected(self):
        self.assert_rejects(lambda a,b: b["samples"][300].update(frame=True))

    def test_noninteger_rgb_coordinate_rejected(self):
        self.assert_rejects(lambda a,b: a["slots"][10].update(left=66.5))

    def test_original_published_second_write_anchor_changed(self):
        self.assert_rejects(lambda a,b: b["samples"][144][
            "written_values"].__setitem__(1,100))


if __name__ == "__main__":
    unittest.main()
