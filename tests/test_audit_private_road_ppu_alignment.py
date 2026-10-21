"""Synthetic manifests only. No private FCEUX report or original ROM."""
from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_road_ppu_alignment import ANCHORS,audit

def samples():
    # Invented CPU offsets in documented ranges: NOT source trace excerpts.
    road={"schema":"road_image_cross_sections_v1",
          "rom_sha256":"1"*64,"fm2_sha256":"2"*64,
          "movie_frame_origin":"zero_based_FM2","samples":[]}
    ppu={"schema":"ppu_cpu_writer_phases_v1",
         "rom_sha256":"1"*64,"fm2_sha256":"2"*64,
         "movie_frame_origin":"zero_based_FM2","samples":[]}
    for frame,(left,right,second,post) in ANCHORS.items():
        road["samples"].append({"frame":frame,"left":left,"right":right})
        ppu["samples"].append({
            "frame":frame,
            "writer_pcs":["E8EC","E8F1","E369","E36C"],
            "written_values":[0,second,0,0],
            "cpu_cycles_after_previous_frame":[1000,1007,24286,24290],
            "ram_0d_postframe":post})
    return road,ppu

class NumericRoadPpuAuditTests(unittest.TestCase):
    def expect_bad(self,change):
        a,b=samples()
        change(a,b)
        with self.assertRaises(ValueError):
            audit(a,b)
    def test_valid_independent_synthetic_numeric_join(self):
        a,b=samples()
        result=audit(a,b)
        self.assertEqual(result["joined_frames"],4)
        self.assertEqual(result["published_anchor_frames"],[600,744,800,920])
        self.assertFalse(result["display_effective_scroll_proven"])
        self.assertFalse(result["camera_speed_proven"])
        self.assertFalse(result["road_collision_proven"])
        self.assertNotIn("rom_sha256",result)
    def test_wrong_rom_identity_rejected(self):
        self.expect_bad(lambda a,b:b.update(rom_sha256="a"*64))
    def test_wrong_fm2_identity_rejected(self):
        self.expect_bad(lambda a,b:b.update(fm2_sha256="a"*64))
    def test_malformed_provenance_rejected(self):
        self.expect_bad(lambda a,b:a.update(movie_frame_origin="one_based"))
    def test_missing_image_anchor_rejected(self):
        self.expect_bad(lambda a,b:a["samples"].pop(1))
    def test_missing_cpu_pair_rejected(self):
        self.expect_bad(lambda a,b:b["samples"].pop(1))
    def test_changed_source_road_edge_rejected(self):
        self.expect_bad(lambda a,b:a["samples"][2].update(right=156))
    def test_changed_source_writer_value_rejected(self):
        self.expect_bad(lambda a,b:b["samples"][1]["written_values"].__setitem__(1,137))
    def test_changed_postframe_ram_rejected(self):
        self.expect_bad(lambda a,b:b["samples"][3].update(ram_0d_postframe=20))
    def test_wrong_writer_pc_rejected(self):
        self.expect_bad(lambda a,b:b["samples"][2]["writer_pcs"].__setitem__(2,"E368"))
    def test_missing_late_zero_write_rejected(self):
        self.expect_bad(lambda a,b:b["samples"][2]["written_values"].__setitem__(3,1))
    def test_wrong_first_cycle_gap_rejected(self):
        self.expect_bad(lambda a,b:b["samples"][0]["cpu_cycles_after_previous_frame"].__setitem__(1,1006))
    def test_wrong_late_cycle_gap_rejected(self):
        self.expect_bad(lambda a,b:b["samples"][0]["cpu_cycles_after_previous_frame"].__setitem__(3,24291))
    def test_late_phase_unsupported_rejected(self):
        self.expect_bad(lambda a,b:b["samples"][0]["cpu_cycles_after_previous_frame"].__setitem__(2,24000))
    def test_duplicate_frame_rejected(self):
        self.expect_bad(lambda a,b:a["samples"].insert(1,copy.deepcopy(a["samples"][0])))
    def test_boolean_numeric_field_rejected(self):
        self.expect_bad(lambda a,b:a["samples"][0].update(left=True))
    def test_unexpected_media_or_absolute_path_field_rejected(self):
        self.expect_bad(lambda a,b:a.update(source_rom_file="/private/original.nes"))
    def test_extra_source_frame_with_real_pair_joined(self):
        a,b=samples()
        a["samples"].insert(2,{"frame":760,"left":82,"right":173})
        b["samples"].insert(2,{
            "frame":760,
            "writer_pcs":["E8EC","E8F1","E369","E36C"],
            "written_values":[0,100,0,0],
            "cpu_cycles_after_previous_frame":[1200,1207,24285,24289],
            "ram_0d_postframe":95
        })
        self.assertEqual(audit(a,b)["joined_frames"],5)

if __name__=="__main__":
    unittest.main()
