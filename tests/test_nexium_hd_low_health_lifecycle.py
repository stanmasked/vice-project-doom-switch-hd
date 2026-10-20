#!/usr/bin/env python3
"""Adversarial visual lifecycle checks: HP2 ON/OFF then death/retry."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_nexium_hd_low_health_lifecycle import (
    source_hearts, verify_lifecycle,
)

W, H = 1280, 720
CHIPS = ((757, 766), (771, 781), (786, 795), (800, 810), (814, 824))


def rect(buffer, x0, x1, y0, y1, rgb):
    color = bytes(rgb)
    for y in range(y0, y1):
        for x in range(x0, x1):
            i = (y * W + x) * 3
            buffer[i:i+3] = color


def frame(hp, warning=False, hit_pulse=False):
    pixels = bytearray(W * H * 3)
    for i, (left, right) in enumerate(CHIPS):
        color = (255, 220, 153) if i < hp and hit_pulse else (
            (106, 198, 174) if i < hp else (55, 64, 79)
        )
        rect(pixels, left, right+1, 17, 29, color)
    if warning:
        rect(pixels, 757, 836, 34, 37, (237, 115, 112))
        rect(pixels, 846, 856, 17, 25, (255, 171, 147))
    return pixels


class TestRealHudSequence(unittest.TestCase):
    def test_authentic_four_state_pixels(self):
        out = verify_lifecycle(frame(2, warning=True), frame(2),
                               frame(0), frame(5))
        self.assertEqual(out, {"warning_line": 237, "warning_label": 80})

    def test_yellow_flash_still_counts_as_real_healthy_heart(self):
        self.assertEqual(
            verify_lifecycle(frame(2, warning=True, hit_pulse=True),
                             frame(2, hit_pulse=True), frame(0), frame(5))[
                "warning_line"], 237)

    def test_reject_a_low_hp_label_on_the_death_screen(self):
        with self.assertRaisesRegex(ValueError, "leaked into death"):
            verify_lifecycle(frame(2, True), frame(2), frame(0, True), frame(5))

    def test_reject_low_hp_still_on_after_replay(self):
        with self.assertRaisesRegex(ValueError, "leaked into restart"):
            verify_lifecycle(frame(2, True), frame(2), frame(0), frame(5, True))

    def test_reject_warning_that_did_not_pulse_off(self):
        with self.assertRaisesRegex(ValueError, "leaked into quiet"):
            verify_lifecycle(frame(2, True), frame(2, True), frame(0), frame(5))

    def test_reject_fake_hp2_label_on_five_full_hearts(self):
        with self.assertRaisesRegex(ValueError, "source heart"):
            verify_lifecycle(frame(5, True), frame(2), frame(0), frame(5))

    def test_reject_fifth_chip_not_reset_after_minus(self):
        retry = frame(5)
        rect(retry, 814, 825, 17, 29, (55, 64, 79))
        with self.assertRaisesRegex(ValueError, "source heart"):
            verify_lifecycle(frame(2, True), frame(2), frame(0), retry)

    def test_reject_partial_corruption_of_live_heart(self):
        on = frame(2, True)
        rect(on, 758, 765, 19, 27, (55, 64, 79))
        with self.assertRaisesRegex(ValueError, "source heart"):
            verify_lifecycle(on, frame(2), frame(0), frame(5))

    def test_reject_hidden_heart_on_death_screen(self):
        dead = frame(0)
        rect(dead, 759, 763, 19, 27, (106, 198, 174))
        with self.assertRaisesRegex(ValueError, "source heart"):
            verify_lifecycle(frame(2, True), frame(2), dead, frame(5))

    def test_reject_incorrect_frame_dimensions(self):
        with self.assertRaises(ValueError):
            verify_lifecycle(frame(2, True), frame(2)[:-3], frame(0), frame(5))


if __name__ == "__main__":
    unittest.main()
