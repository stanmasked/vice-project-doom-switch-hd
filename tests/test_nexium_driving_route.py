import sys
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_nexium_driving_route import verify_trace, verify_evidence



SCREENSHOTS = ("screen-exit-road.png", "screen-exit-black.png", "screen-exit-platform.png")
FINGERPRINT = "29fdf781dfd4ec22"


def png_bytes(width=1280, height=720, color=(20, 30, 40)):
    row = b"\x00" + bytes(color) * width
    raw = row * height

    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload +
                struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


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


    @staticmethod
    def exit_fixture():
        lines = []
        for seq in range(43):
            if seq == 0:
                scene, black_frames, black_pixel = "last_road", 0, 0
            elif seq <= 41:
                scene, black_frames, black_pixel = "black", seq, 1
            else:
                scene, black_frames, black_pixel = "platform", 41, 0
            lines.append(
                f"VPD_DRIVING_EXIT_V1 seq={seq} scene={scene} road_frame=3197 "
                f"black_frames={black_frames} black_pixel={black_pixel} "
                f"platform_before={FINGERPRINT} platform_after={FINGERPRINT} "
                "source=libnx_frame original_stage_clear_proven=0"
            )
        return lines

    def write_bundle(self, directory):
        directory = Path(directory)
        (directory / "guest-driving-route-witness.txt").write_text(
            "\n".join(self.fixture()) + "\n", encoding="ascii")
        (directory / "guest-driving-exit-witness.txt").write_text(
            "\n".join(self.exit_fixture()) + "\n", encoding="ascii")
        (directory / "host-route-input.txt").write_text("\n".join([
            "host_route_completion=observed manual_minus_sent=no",
            "native_transition_last_road=yes seq=0",
            "native_transition_black=yes seq=17",
            "native_transition_black=yes seq=41",
            "native_transition_platform=yes seq=42",
            "VPD_NEXIUM_DRIVING_ROUTE_PROBE_PASS",
        ]) + "\n", encoding="ascii")
        for name in SCREENSHOTS:
            (directory / name).write_bytes(png_bytes())

    def test_complete_evidence_bundle_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            self.write_bundle(temp)
            result = verify_evidence(Path(temp))
            self.assertEqual(result["exit_records"], 43)
            self.assertEqual(result["screenshots"], 3)
            self.assertEqual(result["frame"], 3197)

    def test_host_manual_exit_claim_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            self.write_bundle(temp)
            path = Path(temp) / "host-route-input.txt"
            path.write_text(path.read_text().replace(
                "manual_minus_sent=no", "manual_minus_sent=yes"))
            with self.assertRaises(ValueError):
                verify_evidence(Path(temp))

    def test_missing_blackout_record_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            self.write_bundle(temp)
            path = Path(temp) / "guest-driving-exit-witness.txt"
            lines = path.read_text().splitlines()
            del lines[21]
            path.write_text("\n".join(lines) + "\n")
            with self.assertRaises(ValueError):
                verify_evidence(Path(temp))

    def test_changed_transition_fingerprint_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            self.write_bundle(temp)
            path = Path(temp) / "guest-driving-exit-witness.txt"
            lines = path.read_text().splitlines()
            lines[42] = lines[42].replace(
                f"platform_after={FINGERPRINT}", "platform_after=29fdf781dfd4ec23")
            path.write_text("\n".join(lines) + "\n")
            with self.assertRaises(ValueError):
                verify_evidence(Path(temp))

    def test_missing_transition_screenshot_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            self.write_bundle(temp)
            (Path(temp) / "screen-exit-black.png").unlink()
            with self.assertRaises(ValueError):
                verify_evidence(Path(temp))

    def test_wrong_screenshot_dimensions_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            self.write_bundle(temp)
            (Path(temp) / "screen-exit-platform.png").write_bytes(png_bytes(640, 480))
            with self.assertRaises(ValueError):
                verify_evidence(Path(temp))

    def test_screenshot_crc_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            self.write_bundle(temp)
            path = Path(temp) / "screen-exit-road.png"
            data = bytearray(path.read_bytes())
            data[-5] ^= 0x01
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                verify_evidence(Path(temp))


if __name__ == "__main__":
    unittest.main()
