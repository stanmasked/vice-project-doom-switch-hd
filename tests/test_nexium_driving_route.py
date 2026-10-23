import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_nexium_driving_route import verify_trace


class DrivingRouteAuditTests(unittest.TestCase):
    @staticmethod
    def fixture():
        pass_frames = [91 + 109 * n for n in range(30)]
        frames = set(range(16, 3185, 16))
        frames.update(frame for frame in pass_frames if frame <= 3184)
        lines = []
        for seq, frame in enumerate(sorted(frames), 1):
            passed = sum(p <= frame for p in pass_frames)
            serial = passed
            if serial == 0:
                obstacle_x = 640
                obstacle_y = 20 + 7 * frame
            else:
                obstacle_x = (440, 570, 710, 840)[serial % 4]
                last_pass = pass_frames[serial - 1]
                obstacle_y = -110 + 7 * (frame - last_pass)
            if frame == 16:
                car_x, left, right = 640, 0, 0
            else:
                car_x = {640: 810, 570: 810, 710: 560, 840: 600, 440: 700}[obstacle_x]
                if frame < 300:
                    left, right = 0, 1
                elif frame < 700:
                    left, right = 1, 0
                elif frame < 1100:
                    left, right = 0, 1
                elif frame < 1500:
                    left, right = 1, 0
                else:
                    left, right = ((1, 0) if frame % 32 < 16 else (0, 1))
            lines.append(
                f"VPD_DRIVING_ROUTE_V1 seq={seq} event=sample frame={frame} "
                f"car_x={car_x} lateral_velocity=0 speed=3 health=5 cooldown=0 "
                f"impacts=0 obstacles_passed={passed} obstacle_serial={serial} "
                f"obstacle_x={obstacle_x} obstacle_y={obstacle_y} "
                f"left={left} right={right} throttle=0 brake=0 "
                "platform_fp=29fdf781dfd4ec22 source=libnx_pad "
                "manual_exit=0 route_complete=0 original_stage_clear_proven=0"
            )
        passed = sum(p <= 3197 for p in pass_frames)
        serial = passed
        obstacle_x = (440, 570, 710, 840)[serial % 4]
        last_pass = pass_frames[serial - 1]
        obstacle_y = -110 + 7 * (3197 - last_pass)
        lines.append(
            f"VPD_DRIVING_ROUTE_V1 seq={len(lines)+1} event=exit_request "
            f"frame=3197 car_x=730 lateral_velocity=0 speed=3 health=5 cooldown=0 "
            f"impacts=0 obstacles_passed={passed} obstacle_serial={serial} "
            f"obstacle_x={obstacle_x} obstacle_y={obstacle_y} "
            "left=0 right=0 throttle=0 brake=0 "
            "platform_fp=29fdf781dfd4ec22 source=libnx_frame "
            "manual_exit=0 route_complete=1 original_stage_clear_proven=0"
        )
        return lines

    def test_complete_live_route_passes(self):
        result = verify_trace("\n".join(self.fixture()))
        self.assertEqual(result["frame"], 3197)
        self.assertGreaterEqual(result["passed"], 8)
        self.assertEqual(result["health"], 5)
        self.assertGreaterEqual(result["samples"], 180)

    def test_manual_exit_cannot_claim_route_completion(self):
        lines = self.fixture()
        lines[-1] = lines[-1].replace("manual_exit=0", "manual_exit=1")
        with self.assertRaises(ValueError):
            verify_trace("\n".join(lines))

    def test_early_exit_rejected(self):
        lines = self.fixture()
        lines[-1] = lines[-1].replace("frame=3197", "frame=3196")
        with self.assertRaises(ValueError):
            verify_trace("\n".join(lines))

    def test_missing_obstacle_progress_rejected(self):
        lines = self.fixture()
        lines[-1] = lines[-1].replace(f"obstacles_passed={sum(p <= 3197 for p in [91 + 109*n for n in range(30)])}",
                                      "obstacles_passed=7")
        with self.assertRaises(ValueError):
            verify_trace("\n".join(lines))

    def test_forged_original_stage_clear_rejected(self):
        lines = self.fixture()
        lines[-1] = lines[-1].replace("original_stage_clear_proven=0",
                                      "original_stage_clear_proven=1")
        with self.assertRaises(ValueError):
            verify_trace("\n".join(lines))

    def test_changed_platform_state_rejected(self):
        lines = self.fixture()
        lines[-1] = lines[-1].replace("platform_fp=29fdf781dfd4ec22",
                                      "platform_fp=29fdf781dfd4ec23")
        with self.assertRaises(ValueError):
            verify_trace("\n".join(lines))

    def test_non_pad_sample_rejected(self):
        lines = self.fixture()
        lines[10] = lines[10].replace("source=libnx_pad", "source=host_input")
        with self.assertRaises(ValueError):
            verify_trace("\n".join(lines))

    def test_missing_steering_rejected(self):
        lines = self.fixture()
        lines = [line.replace("left=1", "left=0").replace("right=1", "right=0")
                 for line in lines]
        with self.assertRaises(ValueError):
            verify_trace("\n".join(lines))


if __name__ == "__main__":
    unittest.main()
