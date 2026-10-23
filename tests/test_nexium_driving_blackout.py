import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_nexium_driving_blackout import verify_records

class SourceBlackoutAuditTests(unittest.TestCase):
    @staticmethod
    def fixture():
        lines=[]
        for n in range(43):
            scene="last_road" if n==0 else "platform" if n==42 else "black"
            lines.append(
                f"VPD_DRIVING_EXIT_V1 seq={n} scene={scene} "
                f"road_frame=20 black_frames={min(n,41)} "
                f"black_pixel={int(scene=='black')} "
                f"platform_before={'ab'*8} platform_after={'ab'*8} "
                "source=libnx_frame original_stage_clear_proven=0"
            )
        return lines
    def test_synthetic_good(self):
        verify_records(self.fixture())
    def test_missing_black_frame(self):
        lines=self.fixture()
        del lines[23]
        with self.assertRaises(ValueError):verify_records(lines)
    def test_changed_platform_rejected(self):
        lines=self.fixture()
        lines[40]=lines[40].replace("platform_after="+"ab"*8,
                                    "platform_after="+"aa"*8)
        with self.assertRaises(ValueError):verify_records(lines)
    def test_nonblack_pixel_rejected(self):
        lines=self.fixture()
        lines[18]=lines[18].replace("black_pixel=1","black_pixel=0")
        with self.assertRaises(ValueError):verify_records(lines)
    def test_duplicate_record_rejected(self):
        lines=self.fixture()
        lines[10]=lines[9]
        with self.assertRaises(ValueError):verify_records(lines)
    def test_black_frame_counter_regression_rejected(self):
        lines=self.fixture()
        lines[17]=lines[17].replace("black_frames=17","black_frames=16")
        with self.assertRaises(ValueError):verify_records(lines)
    def test_road_state_changes_during_blackout_rejected(self):
        lines=self.fixture()
        lines[25]=lines[25].replace("road_frame=20","road_frame=21")
        with self.assertRaises(ValueError):verify_records(lines)
    def test_original_stage_clear_claim_rejected(self):
        lines=self.fixture()
        lines[42]=lines[42].replace("original_stage_clear_proven=0",
                                    "original_stage_clear_proven=1")
        with self.assertRaises(ValueError):verify_records(lines)
    def test_forged_host_source_rejected(self):
        lines=self.fixture()
        lines[31]=lines[31].replace("source=libnx_frame","source=host_input")
        with self.assertRaises(ValueError):verify_records(lines)
if __name__=="__main__":
    unittest.main()
