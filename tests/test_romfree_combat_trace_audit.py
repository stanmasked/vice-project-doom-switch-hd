"""ROM-free full-CSV auditor unit tests (no original ROM or Switch assets)."""
import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_romfree_combat_trace import (
    EXPECTED_SHA256, FIELDS, SAMPLES, TraceError, audit,
    expected_buttons)


def fixture():
    # Generated independently of C++: tests only parser structure.
    # The separate CMake test requires actual compiled-C++ full-trace SHA.
    lines = [",".join(FIELDS)]
    for frame in range(1, 201):
        fields = (
            frame, expected_buttons(frame), 12288, 53760, 0, 0,
            3, 0, 0, frame
        )
        lines.append(",".join(map(str, fields)))
    return ("\n".join(lines) + "\n").encode("ascii")


class FullTraceUnitTests(unittest.TestCase):
    def test_expected_reference_and_input_schedule(self):
        self.assertEqual(len(EXPECTED_SHA256), 64)
        self.assertEqual(len(SAMPLES), 4)
        self.assertEqual([expected_buttons(f) for f in
                          (1, 110, 111, 115, 116, 145,
                           146, 150, 151, 175, 176, 200)],
                         [8, 8, 0, 0, 2, 2, 5, 5, 1, 1, 0, 0])

    def test_structural_positive_only_with_explicit_fake_reference(self):
        payload = fixture()
        with patch.dict(SAMPLES, {}, clear=True):
            observed = audit(payload, sha256=hashlib.sha256(payload).hexdigest())
        self.assertEqual(observed["frames"], 200)
        self.assertEqual(observed["shots"], 0)
        self.assertFalse(observed["original_game_proven"])
        self.assertFalse(observed["switch_runtime_proven"])
        with self.assertRaises(TraceError):
            audit(payload)  # must not accept toy data as real golden trace

    def test_mutations_cannot_be_certified(self):
        normal = fixture()
        cases = [
            b"", normal[:-1], normal + b"extra\n",
            normal.replace(b"\n", b"\r\n"),
            normal.replace(b"frame,buttons", b"frame,fake_buttons", 1),
            normal.replace(b"1,8,12288", b"1,0,12288", 1),
            normal.replace(b"58,8,12288", b"58,0,12288", 1),
            normal.replace(b"200,0,12288", b"200,1,12288", 1),
            normal.replace(b"1,8,12288", b"01,8,12288", 1),
            normal.replace(b"1,8,12288", b"1,8,nan", 1),
            normal.replace(b"1,8,12288", b"1,8,-99", 1),
            normal.replace(b"1,8,12288", b"1,8,12288,0", 1),
            normal.replace(b"1,8,12288", b"1,8,12288,", 1),
            normal.replace(b"1,8,12288", b"1,8,12288\x00", 1),
            normal.replace(b"1,8,12288", b"1,8,12288\xff", 1),
            normal.replace(b"2,8,12288", b"1,8,12288", 1),
        ]
        with patch.dict(SAMPLES, {}, clear=True):
            for n, mutated in enumerate(cases):
                with self.subTest(mutation=n), self.assertRaises(TraceError):
                    audit(mutated, sha256=hashlib.sha256(mutated).hexdigest())

    def test_noncanonical_counts_and_cross_frame_damage(self):
        lines = fixture().decode("ascii").splitlines()
        # A hit cannot restore the target's health and cannot occur
        # without a projectile having been fired.
        lines[10] = "10,8,12288,53760,0,0,2,1,0,10"
        payload = ("\n".join(lines) + "\n").encode("ascii")
        with patch.dict(SAMPLES, {}, clear=True):
            with self.assertRaises(TraceError):
                audit(payload, sha256=hashlib.sha256(payload).hexdigest())


if __name__ == "__main__":
    unittest.main()
