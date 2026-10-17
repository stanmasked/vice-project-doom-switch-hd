"""Stage112 pinned synthetic subscanline MMC3 write-phase acceptance tests."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from make_stage110_synthetic_midframe_rom import make_rom, program
from run_stage112_native_subscanline_sweep import (
    PHASES, SweepError, validate_sweep,
)


def sample(phase, switch_xt, new_xt, *, sl=104, new_sl=None):
    return (phase, {
        "switch_source_scanline": sl,
        "last_rendered_xt": switch_xt,
        "first_new_source_scanline": sl if new_sl is None else new_sl,
        "first_new_xt": new_xt,
        "same_buffered_tile_frame_proven": True,
        "original_game_tile_proven": False,
    })


class SyntheticRom(unittest.TestCase):
    def test_nop_phase_only_inserts_bounded_cpu_noops(self):
        baseline = program()
        for phase in PHASES[1:]:
            with self.subTest(phase=phase):
                changed = program(phase_nops=phase)
                self.assertEqual(len(changed), len(baseline) + phase)
                self.assertEqual(changed.count(bytes((0xea,))), phase)
                self.assertIn(bytes((0xa9, 1, 0x8d, 1, 0x80)), changed)

    def test_bank_data_unchanged_across_phase_sweep(self):
        with tempfile.TemporaryDirectory() as folder:
            outputs = []
            for phase in PHASES:
                target = Path(folder) / ("p%d.nes" % phase)
                make_rom(target, phase_nops=phase)
                outputs.append(target.read_bytes())
            self.assertTrue(all(len(data) == 49168 for data in outputs))
            self.assertEqual(len({data[-16384:] for data in outputs}), 1)
            self.assertEqual(len({data[:16] for data in outputs}), 1)
            self.assertEqual(len({data[16:-16384] for data in outputs}), len(PHASES))

    def test_negative_and_excessive_phases_rejected(self):
        for phase in (-1, 65, 10000, 1.5):
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                program(phase_nops=phase)


class SweepValidation(unittest.TestCase):
    def setUp(self):
        self.valid = [
            sample(0, 1, 5),
            sample(4, 4, 8),
            sample(8, 7, 11),
            sample(12, 10, 14),
        ]

    def test_accepts_monotone_subscanline_transition(self):
        result = validate_sweep(self.valid)
        self.assertEqual(result["relative_first_new_tiles"], [0, 3, 6, 9])
        self.assertFalse(result["original_game_raster_proven"])

    def test_rejects_reorder_duplicate_and_missing_phase(self):
        for wrong in (self.valid[:-1],
                      [self.valid[0], self.valid[0], *self.valid[2:]],
                      list(reversed(self.valid))):
            with self.subTest(case=len(wrong)), self.assertRaises(SweepError):
                validate_sweep(wrong)

    def test_rejects_unmoving_reversing_and_out_of_line(self):
        for wrong in (
            [sample(0, 1, 5), sample(4, 1, 8),
             sample(8, 7, 11), sample(12, 10, 14)],
            [sample(0, 1, 5), sample(4, 4, 8),
             sample(8, 7, 7), sample(12, 10, 14)],
            [sample(0, 1, 5), sample(4, 4, 8),
             sample(8, 7, 11, sl=105), sample(12, 10, 14)],
            [sample(0, 1, 5), sample(4, 4, 8),
             sample(8, 7, 11), sample(12, 10, 20)],
        ):
            with self.assertRaises(SweepError):
                validate_sweep(wrong)

    def test_rejects_unsupported_real_game_or_absent_native_evidence(self):
        for key, value in (("original_game_tile_proven", True),
                           ("same_buffered_tile_frame_proven", False)):
            changed = [(phase, dict(info)) for phase, info in self.valid]
            changed[2][1][key] = value
            with self.assertRaises(SweepError):
                validate_sweep(changed)


if __name__ == "__main__":
    unittest.main()
