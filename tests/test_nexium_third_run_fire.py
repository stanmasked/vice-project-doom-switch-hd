"""Reject impossible/forged third-run fire and hit; real NeXium runs separately."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "third_run_fire",ROOT/"tools/audit_nexium_third_run_fire.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def fixture():
    return (
        b"VPD_ROMFREE_THIRD_FIRE_V1 seq=1 event=fire frame=25 "
        b"hero_x=16896 hero_hp=5 guard_hp=3 guard_hits=0 "
        b"guard_attacks=0 shots=1 sentry_hp=2 wave=0 clear=0 dash=0 "
        b"input_fire=1 source=live_guest original_game_proven=no\n"
        b"VPD_ROMFREE_THIRD_FIRE_V1 seq=2 event=impact frame=60 "
        b"hero_x=16896 hero_hp=5 guard_hp=2 guard_hits=1 "
        b"guard_attacks=0 shots=1 sentry_hp=2 wave=0 clear=0 dash=0 "
        b"input_fire=0 source=live_guest original_game_proven=no\n"
    )

class ThirdRunFireAuditTests(unittest.TestCase):
    def test_one_guest_fired_bullet_and_one_swept_hit(self):
        self.assertEqual(m.verify(fixture()),
                         {"fire_frame":25,"hit_frame":60,"hero_x":16896})
    def test_reject_forged_timing_hps_events_and_source(self):
        raw=fixture()
        cases=[
            b"",raw[:-1],raw+raw,raw.replace(b"\n",b"\r\n"),
            raw.replace(b"seq=1",b"seq=01",1),
            raw.replace(b"event=impact",b"event=fire",1),
            raw.replace(b"frame=60",b"frame=25",1),
            raw.replace(b"frame=60",b"frame=115",1),
            raw.replace(b"hero_x=16896",b"hero_x=16897",1),
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
            raw.replace(b"original_game_proven=no",
                        b"original_game_proven=yes",1),
        ]
        for i,case in enumerate(cases):
            with self.subTest(i=i),self.assertRaises((ValueError,UnicodeError)):
                m.verify(case)
    def test_not_accepted_without_real_x11_and_prior_guest_events(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            (base/"guest-post-defeat-fire-witness.txt").write_bytes(fixture())
            with self.assertRaisesRegex(ValueError,"movement witness absent"):
                m.audit(base)
            (base/"guest-post-defeat-control-witness.txt").write_bytes(
                b"VPD_ROMFREE_THIRD_RUN_V1 event=move frame=20 before_frame=19 "
                b"before_x=16384 after_x=16896 delta_fixed=512 hero_hp=5 "
                b"guard_hp=3 guard_attacks=0 sentry_hp=2 shots=0 dash=0 "
                b"wave=0 clear=0 input_right=1 source=live_guest "
                b"original_game_proven=no\n")
            with self.assertRaisesRegex(ValueError,"proof missing"):
                m.audit(base)

if __name__=="__main__":
    unittest.main()
