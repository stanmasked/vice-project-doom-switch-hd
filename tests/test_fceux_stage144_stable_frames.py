"""Stage144 byte-exact terminal-jump relocation in synthetic two-frame ROMs."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from make_stage110_synthetic_midframe_rom import program
from make_stage141_frame_reset_rom import make_rom as make_old
from make_stage144_stable_frame_rom import (
    BANK_SIZE, LOAD_ADDR, MODES, PRG_START, PRG_END, make_rom,
    relocation_sites, relocate,
)


class TerminalLoopRegression(unittest.TestCase):
    def test_stage141_original_jmp_was_stale(self):
        with tempfile.TemporaryDirectory() as td:
            for mode in MODES:
                with self.subTest(mode=mode):
                    old = Path(td) / (mode + "_old.nes")
                    make_old(old, mode)
                    original = old.read_bytes()
                    sites = relocation_sites(original)
                    old_target = LOAD_ADDR + len(program()) - 3
                    self.assertEqual(len(sites), 4)
                    self.assertLess(old_target, LOAD_ADDR + sites[0][1])
                    self.assertEqual([relative for _, relative in sites],
                                     [sites[0][1]] * 4)
                    for start, relative in sites:
                        self.assertEqual(
                            int.from_bytes(original[
                                start+relative+1:start+relative+3], "little"),
                            old_target)
                        self.assertEqual(original[start+relative], 0x4C)

    def test_repair_changes_only_eight_prg_address_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            for mode in MODES:
                with self.subTest(mode=mode):
                    old = Path(td) / (mode + "_old.nes")
                    repaired = Path(td) / (mode + "_stable.nes")
                    make_old(old, mode)
                    digest = make_rom(repaired, mode)
                    baseline = old.read_bytes()
                    actual = repaired.read_bytes()
                    self.assertEqual(actual, relocate(baseline))
                    self.assertEqual(hashlib.sha256(actual).hexdigest(), digest)
                    self.assertEqual(len(actual), 49168)
                    self.assertEqual(actual[:PRG_START], baseline[:PRG_START])
                    self.assertEqual(actual[PRG_END:], baseline[PRG_END:])
                    sites = relocation_sites(baseline)
                    expected = {
                        start + relative + offset for start, relative in sites
                        for offset in (1, 2)
                    }
                    diffs = {i for i, (a, b) in enumerate(zip(baseline, actual))
                             if a != b}
                    self.assertEqual(diffs, expected)
                    for start, relative in sites:
                        self.assertEqual(actual[start+relative], 0x4C)
                        self.assertEqual(
                            int.from_bytes(actual[
                                start+relative+1:start+relative+3], "little"),
                            LOAD_ADDR + relative)
                        # No more CPU instructions after the infinite JMP.
                        end = BANK_SIZE - 6 if start == PRG_START + 3*BANK_SIZE else BANK_SIZE
                        self.assertEqual(actual[
                            start+relative+3:start+end],
                            bytes([0xEA])*(end-relative-3))
                    self.assertEqual(actual[PRG_END-6:PRG_END],
                                     b"\\x00\\xC0"*3)

    def test_malformed_or_prepatched_rom_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            old = Path(td) / "old.nes"
            make_old(old, "nine_overflow")
            original = old.read_bytes()
            sites = relocation_sites(original)
            for bad in (
                b"", original[:-1], original[:16] + b"garbage" + original[23:],
                relocate(original),
                original[:sites[0][0]+sites[0][1]] + b"\\xea" +
                    original[sites[0][0]+sites[0][1]+1:],
                original[:sites[0][0]+sites[0][1]+3] + b"\\x00" +
                    original[sites[0][0]+sites[0][1]+4:],
            ):
                with self.subTest(size=len(bad)):
                    with self.assertRaises(ValueError):
                        relocate(bad)
            self.assertEqual(original, old.read_bytes())

    def test_invalid_modes_do_not_publish_file(self):
        with tempfile.TemporaryDirectory() as td:
            for bad in ("", "ninth_offscreen", "nine_8x16", True, None):
                with self.subTest(bad=bad):
                    dest = Path(td) / "unsupported.nes"
                    with self.assertRaises(ValueError):
                        make_rom(dest, bad)
                    self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
