"""Reject forged third-playthrough wave/exit records (not live proof)."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "third_stage",ROOT/"tools/audit_nexium_third_stage.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def valid():
    return (
        b"VPD_ROMFREE_THIRD_STAGE_V1 seq=1 event=wave frame=250 "
        b"hero_x=107008 hero_hp=5 guard_hp=0 guard_hits=3 "
        b"sentry_hp=2 sentry_hits=0 wave=1 clear=0 "
        b"input_right=1 input_fire=0 source=live_guest "
        b"original_game_proven=no\n"
        b"VPD_ROMFREE_THIRD_STAGE_V1 seq=2 event=exit frame=470 "
        b"hero_x=225280 hero_hp=3 guard_hp=0 guard_hits=3 "
        b"sentry_hp=0 sentry_hits=2 wave=1 clear=1 "
        b"input_right=1 input_fire=1 source=live_guest "
        b"original_game_proven=no\n"
    )

class ThirdStageAuditTests(unittest.TestCase):
    def test_valid_second_full_completion_after_defeat(self):
        self.assertEqual(m.verify(valid()),
                         {"wave_frame":250,"exit_frame":470,"exit_x":225280})
    def test_malicious_order_timestamp_damage_and_control(self):
        raw=valid()
        parts=raw.splitlines(keepends=True)
        cases=[
            b"",raw[:-1],raw+raw,b"".join(reversed(parts)),
            raw.replace(b"\n",b"\r\n"),
            raw.replace(b"seq=1",b"seq=01",1),
            raw.replace(b"event=exit",b"event=wave",1),
            raw.replace(b"frame=250",b"frame=470",1),
            raw.replace(b"frame=470",b"frame=250",1),
            raw.replace(b"hero_hp=5",b"hero_hp=0",1),
            raw.replace(b"hero_x=107008",b"hero_x=20000",1),
            raw.replace(b"hero_x=225280",b"hero_x=107008",1),
            raw.replace(b"guard_hp=0",b"guard_hp=1",1),
            raw.replace(b"guard_hits=3",b"guard_hits=2",1),
            raw.replace(b"sentry_hp=2",b"sentry_hp=1",1),
            raw.replace(b"sentry_hp=0",b"sentry_hp=1",1),
            raw.replace(b"sentry_hits=0",b"sentry_hits=1",1),
            raw.replace(b"sentry_hits=2",b"sentry_hits=1",1),
            raw.replace(b"wave=1",b"wave=0",1),
            raw.replace(b"clear=0",b"clear=1",1),
            raw.replace(b"clear=1",b"clear=0",1),
            raw.replace(b"input_right=1",b"input_right=0",1),
            raw.replace(b"input_fire=1",b"input_fire=0",1),
            raw.replace(b"source=live_guest",b"source=scripted",1),
            raw.replace(b"original_game_proven=no",
                        b"original_game_proven=yes",1),
        ]
        for i,case in enumerate(cases):
            with self.subTest(i=i),self.assertRaises((ValueError,UnicodeError)):
                m.verify(case)
    def test_cannot_avoid_prior_guard_or_real_x11_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            (base/"guest-third-stage-witness.txt").write_bytes(valid())
            with self.assertRaisesRegex(ValueError,"guard defeat absent"):
                m.audit(base)

if __name__=="__main__":
    unittest.main()
