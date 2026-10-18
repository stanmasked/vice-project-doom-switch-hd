"""Mutation tests for a native-guest scripted guard-combat report.

These fixtures verify the parser; they do not replace NeXium execution.
"""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "guard_combat", ROOT / "tools/audit_nexium_guard_combat.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sample():
    specs = (
        ("alert", "approach", 70, 3, 5, 0, 0, 0, 1),
        ("attack", "approach", 110, 3, 4, 0, 1, 32, 1),
        ("hit1", "shoot", 40, 2, 5, 1, 0, 0, 0),
        ("hit2", "shoot", 50, 1, 5, 2, 0, 0, 0),
        ("defeat", "shoot", 60, 0, 5, 3, 0, 0, 0),
    )
    return "".join(
        "VPD_ROMFREE_GUARD_COMBAT_V1 "
        f"seq={i} event={event} scenario={scenario} frame={frame} "
        f"guard_x=73216 guard_hp={hp} player_hp={player} hits={hits} "
        f"attacks={attacks} cooldown={cd} alerted={alerted} "
        "source=guest_script original_game_proven=no\n"
        for i,(event,scenario,frame,hp,player,hits,attacks,cd,alerted)
        in enumerate(specs,1)
    ).encode("ascii")


class NativeGuardCombatAudit(unittest.TestCase):
    def test_expected_five_distinct_transitions(self):
        self.assertEqual(mod.verify(sample()), {
            "alert_frame":70, "attack_frame":110,
            "hit_frames":[40,50,60]
        })

    def test_reject_omissions_reordered_events_and_forgery(self):
        good=sample()
        rows=good.splitlines(keepends=True)
        mutated=[
            b"",good[:-1],rows[0],good+rows[-1],good+good,
            b"".join([rows[1],rows[0]]+rows[2:]),
            good.replace(b"seq=1",b"seq=01",1),
            good.replace(b"frame=110",b"frame=70"),
            good.replace(b"frame=50",b"frame=39"),
            good.replace(b"guard_hp=0",b"guard_hp=1"),
            good.replace(b"player_hp=4",b"player_hp=5"),
            good.replace(b"hits=3",b"hits=2"),
            good.replace(b"attacks=1",b"attacks=0"),
            good.replace(b"cooldown=32",b"cooldown=31"),
            good.replace(b"alerted=1",b"alerted=0",1),
            good.replace(b"scenario=approach",b"scenario=shoot",1),
            good.replace(b"source=guest_script",b"source=host",1),
            good.replace(b"original_game_proven=no",
                         b"original_game_proven=yes",1),
            good.replace(b"guard_x=73216",b"guard_x=73217",1),
            good.replace(b"\n",b"\r\n"),
            good.replace(b"\n",b"\x00\n"),
            good.replace(b"event=hit1 scenario=shoot",
                         b"scenario=shoot event=hit1"),
        ]
        for i, corrupt in enumerate(mutated):
            with self.subTest(i=i), self.assertRaises(
                (ValueError, UnicodeError)
            ):
                mod.verify(corrupt)

    def test_never_accept_guest_report_without_prior_runtime_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            for name,mark in (
                ("manual-result.txt","VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "),
                ("dash-result.txt","VPD_NEXIUM_GUEST_DASH_PASS "),
                ("guard-result.txt","VPD_NEXIUM_GUARD_PATROL_PASS "),
                ("native-exit-result.txt","VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
            ):
                (base/name).write_text(mark+"ok\n",encoding="ascii")
            with self.assertRaisesRegex(ValueError,"did not create"):
                mod.audit(base)
            (base/"guest-guard-combat-witness.txt").write_bytes(sample())
            mod.audit(base)
            self.assertIn("VPD_NEXIUM_GUARD_COMBAT_SCRIPT_PASS",
                          (base/"guard-combat-result.txt").read_text())
            (base/"guard-result.txt").write_text("INCONCLUSIVE\n")
            with self.assertRaisesRegex(ValueError,"independent"):
                mod.audit(base)

if __name__=="__main__":
    unittest.main()
