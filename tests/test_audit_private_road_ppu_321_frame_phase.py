"""Synthetic-only entire-window CPU phase classification tests."""
from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from test_audit_private_road_ppu_321_trace import fixture
from audit_private_road_ppu_321_frame_phase import validate_clocked_capture

class PrivatePpuFramePhaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        fixture(self.root)
        self.clock=self.root/"road_321_frame_clock.tsv"
        lines=["frame\tbegin_cycle\tend_cycle"]
        for frame in range(600,921):
            lines.append(f"{frame}\t{frame*30000}\t{frame*30000+29780}")
        self.clock.write_text("\n".join(lines)+"\n")
    def tearDown(self):
        self.tmp.cleanup()
    def bad(self,file:str,old:str,new:str):
        path=self.root/file
        data=path.read_text()
        assert old in data
        path.write_text(data.replace(old,new,1))
        with self.assertRaises(ValueError):
            validate_clocked_capture(self.root)
    def test_complete_source_free_frame_phase(self):
        r=validate_clocked_capture(self.root)
        self.assertEqual(r["source_cpu_frame_phases_checked"],1284)
        self.assertEqual(r["frame_boundary_samples"],321)
        self.assertTrue(r["measured_clock_monotonic_between_frames"])
        self.assertFalse(r["effective_ppu_scroll_proven"])
        self.assertFalse(r["source_rom_fm2_sha256_join_verified"])
    def test_missing_frame_boundary(self):
        self.bad("road_321_frame_clock.tsv",
                 "600\t18000000\t18029780\n","")
    def test_reordered_begin_frame(self):
        self.bad("road_321_frame_clock.tsv",
                 "601\t18030000","600\t18030000")
    def test_forged_frame_begin_phase(self):
        self.bad("road_321_frame_clock.tsv",
                 "600\t18000000","600\t18001000")
    def test_forged_writer_after_frame_end(self):
        self.bad("road_321_frame_clock.tsv",
                 "600\t18000000\t18029780","600\t18000000\t18024000")
    def test_nonmonotonic_frame_clock(self):
        self.bad("road_321_frame_clock.tsv",
                 "601\t18030000\t18059780","601\t18020000\t18059780")
    def test_cycle_timestamp_rollover(self):
        self.bad("road_321_frame_clock.tsv",
                 "602\t18060000\t18089780","602\t1200\t30980")
    def test_wrong_late_writer_phase(self):
        self.bad("road_321_writers.tsv",
                 "600\t3\tE369\t00\t18024283",
                 "600\t3\tE369\t00\t18024800")
    def test_missing_source_early_writer(self):
        self.bad("road_321_writers.tsv",
                 "600\t1\tE8EC\t00\t18000800\n","")
    def test_wrong_cpu_frame_clock_header(self):
        self.bad("road_321_frame_clock.tsv",
                 "frame\tbegin_cycle\tend_cycle",
                 "frame\tclock_start\tclock_stop")
    def test_negative_absolute_cycle(self):
        self.bad("road_321_frame_clock.tsv",
                 "600\t18000000\t18029780","600\t-1\t18029780")
    def test_extra_private_path_metadata_is_rejected(self):
        self.bad("road_321_frame_clock.tsv",
                 "600\t18000000\t18029780",
                 "600\t18000000\t18029780\t/private/rom.nes")
    def test_valid_gap_not_same_as_effective_scroll(self):
        self.assertFalse(
            validate_clocked_capture(self.root)["camera_speed_proven"])
if __name__=="__main__":
    unittest.main()
