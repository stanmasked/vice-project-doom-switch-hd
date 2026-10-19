"""Fail-closed fourth native Fire source and visual evidence mutation tests."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "fourth_combat",ROOT/"tools/audit_nexium_fourth_combat.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

def fixture():
    return (
        b"VPD_ROMFREE_FOURTH_COMBAT_V1 seq=1 event=fire frame=28 "
        b"hero_x=16384 hero_hp=5 guard_hp=3 guard_hits=0 "
        b"guard_attacks=0 shots=1 sentry_hp=2 wave=0 clear=0 dash=0 "
        b"input_fire=1 source=live_guest original_game_proven=no\n"
        b"VPD_ROMFREE_FOURTH_COMBAT_V1 seq=2 event=impact frame=69 "
        b"hero_x=16384 hero_hp=5 guard_hp=2 guard_hits=1 "
        b"guard_attacks=0 shots=1 sentry_hp=2 wave=0 clear=0 dash=0 "
        b"input_fire=0 source=live_guest original_game_proven=no\n"
    )

class FourthCombatTests(unittest.TestCase):
    def test_real_one_shot_one_impact_schema(self):
        self.assertEqual(audit.verify(fixture()),{
            "fire_frame":28,"hit_frame":69,"hero_x":16384})

    def test_reject_forged_source_frames_hps_inputs(self):
        raw=fixture()
        cases=[
            b"",raw[:-1],raw+raw,raw.replace(b"\n",b"\r\n"),
            raw.replace(b"FOURTH_COMBAT",b"THIRD_FIRE",1),
            raw.replace(b"seq=1",b"seq=01",1),
            raw.replace(b"event=impact",b"event=fire",1),
            raw.replace(b"frame=69",b"frame=28",1),
            raw.replace(b"frame=69",b"frame=180",1),
            raw.replace(b"hero_x=16384",b"hero_x=16385",1),
            raw.replace(b"hero_hp=5",b"hero_hp=4",1),
            raw.replace(b"guard_hp=3",b"guard_hp=2",1),
            raw.replace(b"guard_hp=2",b"guard_hp=1",1),
            raw.replace(b"guard_hits=0",b"guard_hits=1",1),
            raw.replace(b"guard_hits=1",b"guard_hits=2",1),
            raw.replace(b"guard_attacks=0",b"guard_attacks=1",1),
            raw.replace(b"shots=1",b"shots=2",1),
            raw.replace(b"sentry_hp=2",b"sentry_hp=1",1),
            raw.replace(b"dash=0",b"dash=1",1),
            raw.replace(b"wave=0",b"wave=1",1),
            raw.replace(b"clear=0",b"clear=1",1),
            raw.replace(b"input_fire=1",b"input_fire=0",1),
            raw.replace(b"source=live_guest",b"source=guest_script",1),
            raw.replace(b"original_game_proven=no",b"original_game_proven=yes",1),
        ]
        for idx,changed in enumerate(cases):
            with self.subTest(index=idx),self.assertRaises((ValueError,UnicodeError)):
                audit.verify(changed)

    def test_no_guest_replay_or_x11_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            (base/"guest-fourth-combat-witness.txt").write_bytes(fixture())
            with self.assertRaisesRegex(ValueError,"restart and move"):
                audit.audit(base)
            (base/"guest-fourth-retry-witness.txt").write_bytes(
                b"VPD_ROMFREE_FOURTH_RETRY_V1 seq=1 event=restart "
                b"old_frame=537 old_hp=3 old_guard_hp=0 old_sentry_hp=0 "
                b"old_clear=1 new_frame=0 new_x=12288 hero_hp=5 guard_hp=3 "
                b"sentry_hp=2 wave=0 clear=0 input_minus=1 "
                b"source=live_guest original_game_proven=no\n"
                b"VPD_ROMFREE_FOURTH_RETRY_V1 seq=2 event=move "
                b"frame=20 before_frame=19 before_x=15872 after_x=16384 "
                b"delta_fixed=512 hero_hp=5 guard_hp=3 sentry_hp=2 "
                b"guard_attacks=0 shots=0 wave=0 clear=0 input_right=1 "
                b"source=live_guest original_game_proven=no\n")
            with self.assertRaisesRegex(ValueError,"X11 PASS absent"):
                audit.audit(base)

if __name__=="__main__":
    unittest.main()
