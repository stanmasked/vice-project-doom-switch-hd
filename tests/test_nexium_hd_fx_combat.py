#!/usr/bin/env python3
"""Adversarial parser checks; never replace actual NeXium source evidence."""
import sys
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_nexium_hd_fx_combat import verify,audit

def line(seq,mode,frame,other=0xaabbccdd11223344,actual=0xfedcba9876543210,
         before=0x1234567890abcdef,after=0x1234567890abcdef):
    return (
        f"VPD_HD_FX_COMBAT_V1 seq={seq} mode={mode} frame={frame} "
        "manual=1 l=1 r=1 edge=1 guard_health=2 guard_hits=1 "
        "hero_health=5 wave_active=0 stage_clear=0 "
        f"scene_other={other:016x} scene_displayed={actual:016x} "
        f"roi_pixels=414000 simulation_before={before:016x} "
        f"simulation_after={after:016x} "
        "source=libnx_pad same_frame=yes\n"
    )
GOOD=(line(1,"off",72)+line(2,"on",89)).encode("ascii")

class CombatHDGuestTests(unittest.TestCase):
    def test_source_shape(self):
        self.assertEqual(verify(GOOD),[72,89])

    def test_strict_bad_records(self):
        for value in (
            b"",GOOD[:-1],GOOD+b"extra\n",GOOD.splitlines(True)[0],
            GOOD.replace(b"seq=2",b"seq=1"),
            GOOD.replace(b"mode=on",b"mode=off"),
            GOOD.replace(b"frame=89",b"frame=72"),
            GOOD.replace(b"guard_health=2",b"guard_health=0"),
            GOOD.replace(b"guard_hits=1",b"guard_hits=2"),
            GOOD.replace(b"hero_health=5",b"hero_health=0"),
            GOOD.replace(b"wave_active=0",b"wave_active=1"),
            GOOD.replace(b"stage_clear=0",b"stage_clear=1"),
            GOOD.replace(b"roi_pixels=414000",b"roi_pixels=0"),
            GOOD.replace(b"source=libnx_pad",b"source=host_fixture"),
            GOOD.replace(b"same_frame=yes",b"same_frame=no"),
            GOOD.replace(b"simulation_after=1234567890abcdef",
                         b"simulation_after=1234567890abcdee"),
            GOOD.replace(b"scene_displayed=fedcba9876543210",
                         b"scene_displayed=aabbccdd11223344"),
            GOOD+b"\xff",
        ):
            with self.subTest(record=value[:90]):
                with self.assertRaises(ValueError):verify(value)

    def test_stage_and_host_gates(self):
        with TemporaryDirectory() as tmp:
            base=Path(tmp)
            with self.assertRaises(OSError):audit(base)
            (base/"fourth-combat-result.txt").write_text(
                "VPD_NEXIUM_FOURTH_COMBAT_PASS hit_frame=68\n")
            with self.assertRaises(ValueError):audit(base)
            (base/"guest-hd-fx-combat-witness.txt").write_bytes(GOOD)
            with self.assertRaises(OSError):audit(base)
            (base/"fourth-guard-clear-result.txt").write_text(
                "VPD_NEXIUM_FOURTH_GUARD_CLEAR_PASS frame=116\n")
            with self.assertRaises(OSError):audit(base)
            (base/"input-probe.txt").write_text(
                "host_combat_hd_fx_chord_sent=yes keys=Q+E expected=off guest_seen=yes\n"
                "host_combat_hd_fx_chord_sent=yes keys=Q+E expected=on guest_seen=yes\n")
            (base/"visual-probe.txt").write_text(
                "capture=screen-live-combat-hd-fx-off\n"
                "capture=screen-live-combat-hd-fx-on\n")
            with self.assertRaises(ValueError):audit(base) # no X11 pixels
            (base/"fourth-guard-clear-result.txt").write_text(
                "VPD_NEXIUM_FOURTH_GUARD_CLEAR_PASS frame=80\n")
            with self.assertRaisesRegex(ValueError,"before guard defeat"):
                audit(base)

if __name__=="__main__":
    unittest.main()
