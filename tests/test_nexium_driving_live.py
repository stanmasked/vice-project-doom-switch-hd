import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_nexium_driving_live import verify_trace


class DrivingAuditTests(unittest.TestCase):
    def record(self, seq, event, frame, bx, x, bs, sp, hp0, hp, impact, cooldown,
               left=0, right=0, throttle=0, brake=0, fp="a0" * 8):
        return ("VPD_DRIVING_GUEST_V1 "
                f"seq={seq} event={event} before_frame={max(0, frame-1)} "
                f"frame={frame} before_x={bx} car_x={x} "
                f"before_speed={bs} speed={sp} before_health={hp0} health={hp} "
                f"impacts={impact} cooldown={cooldown} left={left} right={right} "
                f"throttle={throttle} brake={brake} platform_before={fp} "
                f"platform_after={fp} source=libnx_pad original_nes_physics_proven=0")

    def fixture(self):
        return [
            self.record(1, "enter", 0, 640, 640, 3, 3, 5, 5, 0, 0),
            self.record(2, "right_throttle", 1, 640, 642, 3, 4, 5, 5, 0, 0,
                        right=1, throttle=1),
            self.record(3, "left_brake", 4, 644, 642, 4, 2, 5, 5, 0, 0,
                        left=1, brake=1),
            self.record(4, "impact", 45, 640, 640, 8, 6, 5, 4, 1, 45),
            self.record(5, "exit", 48, 640, 640, 6, 6, 4, 4, 1, 42),
        ]

    def test_valid_synthetic_fixture_is_parsable_not_guest_proof(self):
        verify_trace("\n".join(self.fixture()))

    def test_missing_record_fails(self):
        with self.assertRaises(ValueError):
            verify_trace("\n".join(self.fixture()[:-1]))

    def test_platform_mutation_fails(self):
        items = self.fixture()
        items[3] = items[3].replace("platform_after=" + "a0" * 8,
                                    "platform_after=" + "b0" * 8)
        with self.assertRaises(ValueError):
            verify_trace("\n".join(items))

    def test_damage_forgery_fails(self):
        items = self.fixture()
        items[3] = items[3].replace("health=4 impacts=1",
                                    "health=5 impacts=1")
        with self.assertRaises(ValueError):
            verify_trace("\n".join(items))

    def test_host_only_marker_fails(self):
        items = self.fixture()
        items[1] = items[1].replace("source=libnx_pad", "source=host_keyboard")
        with self.assertRaises(ValueError):
            verify_trace("\n".join(items))

    def test_duplicate_line_fails(self):
        items = self.fixture()
        items.append(items[-1])
        with self.assertRaises(ValueError):
            verify_trace("\n".join(items))


if __name__ == "__main__":
    unittest.main()
