#!/usr/bin/env python3
"""Adversarial authored fixtures only; real NeXium guest evidence is required."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_nexium_hd_fx_live import audit,verify

def line(seq,mode,frame,other,shown):
    return (
        f"VPD_HD_FX_LIVE_V1 seq={seq} mode={mode} frame={frame} "
        "right=1 fire=1 moving=1 wave=1 guard_dead=1 "
        "sentry_hp=2 hero_dx_fixed=512 "
        f"scene_other={other:016x} scene_displayed={shown:016x} "
        "roi_pixels=414000 simulation_before=9bd412c3e5a871f0 "
        "simulation_after=9bd412c3e5a871f0 "
        "source=libnx_pad same_frame=yes\n"
    )
GOOD=(
    line(1,"off",320,0x123456789abcdef0,0x124456789abcdef0)+
    line(2,"on",348,0x124456789abcdef0,0x123456789abcdef0)
).encode("ascii")

class LiveCombatProof(unittest.TestCase):
    def test_live_sequence(self):
        rows=verify(GOOD)
        self.assertEqual([320,348],[r[0] for r in rows])
        self.assertEqual([2,2],[r[1] for r in rows])

    def test_reject_host_only_and_corrupt_events(self):
        for data in (
            b"",GOOD[:-1],GOOD+b"extra\n",GOOD.splitlines(True)[0],
            GOOD.replace(b"seq=2",b"seq=1"),
            GOOD.replace(b"mode=on",b"mode=off"),
            GOOD.replace(b"frame=348",b"frame=320"),
            GOOD.replace(b"right=1",b"right=0"),
            GOOD.replace(b"fire=1",b"fire=0"),
            GOOD.replace(b"moving=1",b"moving=0"),
            GOOD.replace(b"wave=1",b"wave=0"),
            GOOD.replace(b"guard_dead=1",b"guard_dead=0"),
            GOOD.replace(b"sentry_hp=2",b"sentry_hp=0"),
            GOOD.replace(b"hero_dx_fixed=512",b"hero_dx_fixed=0"),
            GOOD.replace(b"roi_pixels=414000",b"roi_pixels=0"),
            GOOD.replace(b"source=libnx_pad",b"source=host"),
            GOOD.replace(b"same_frame=yes",b"same_frame=no"),
            GOOD.replace(b"scene_displayed=124456789abcdef0",
                         b"scene_displayed=123456789abcdef0"),
            GOOD.replace(b"simulation_before=9bd412c3e5a871f0",
                         b"simulation_before=9bd412c3e5a871f1"),
            GOOD.replace(b"simulation_after=9bd412c3e5a871f0",
                         b"simulation_after=9bd412c3e5a871f1"),
            GOOD+b"\xff",
        ):
            with self.subTest(data=data[:80]):
                with self.assertRaises(ValueError):
                    verify(data)

    def test_stage_bounds_and_independent_runtime_evidence(self):
        with TemporaryDirectory() as directory:
            base=Path(directory)
            (base/"guest-hd-fx-live-witness.txt").write_bytes(GOOD)
            (base/"fourth-stage-result.txt").write_text(
                "VPD_NEXIUM_FOURTH_STAGE_PASS wave_frame=300 exit_frame=530\n",
                encoding="ascii")
            with self.assertRaises(OSError):
                audit(base) # V2 after-victory proof is independently mandatory
            (base/"hd-fx-guest-result.txt").write_text(
                "VPD_NEXIUM_HD_FX_GUEST_PASS "
                "guest_simulation_unchanged=yes\n",encoding="ascii")
            with self.assertRaises(OSError):
                audit(base) # host pad control history absent
            (base/"input-probe.txt").write_text(
                "".join(
                    "host_hd_fx_live_chord_sent=yes keys=D+Z+Q+E "
                    f"expected={mode} guest_seen=yes capture_before_exit=yes\n"
                    for mode in ("off","on")),encoding="ascii")
            with self.assertRaises(OSError):
                audit(base) # X11 screenshots are required
            (base/"visual-probe.txt").write_text(
                "capture=screen-live-hd-fx-combat-off\n"
                "capture=screen-live-hd-fx-combat-on\n",
                encoding="ascii")
            with self.assertRaisesRegex(ValueError,"PNG not found"):
                audit(base) # host trace cannot replace actual X11 rasters
            (base/"fourth-stage-result.txt").write_text(
                "VPD_NEXIUM_FOURTH_STAGE_PASS wave_frame=325 exit_frame=530\n",
                encoding="ascii")
            with self.assertRaisesRegex(ValueError,"INSIDE active combat"):
                audit(base) # first event before actual wave
            (base/"fourth-stage-result.txt").write_text(
                "VPD_NEXIUM_FOURTH_STAGE_PASS wave_frame=300 exit_frame=340\n",
                encoding="ascii")
            with self.assertRaisesRegex(ValueError,"INSIDE active combat"):
                audit(base) # second event after earned exit

if __name__=="__main__":
    unittest.main()
