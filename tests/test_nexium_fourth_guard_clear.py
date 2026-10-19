"""Verify fourth-run guard death provenance; native X11 tested separately."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "fourth_guard_clear",ROOT/"tools/audit_nexium_fourth_guard_clear.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def sample():
    return (
        b"VPD_ROMFREE_FOURTH_GUARD_CLEAR_V1 event=guard_clear frame=117 "
        b"hero_x=16384 hero_hp=5 guard_hp=0 previous_guard_hp=1 "
        b"guard_hits=3 previous_guard_hits=2 guard_attacks=0 shots=6 "
        b"sentry_hp=2 wave=0 clear=0 dash=0 input_fire=1 "
        b"source=live_guest original_game_proven=no\n"
    )

class FourthGuardClearSourceTests(unittest.TestCase):
    def test_valid_exact_last_swept_hit(self):
        p=m.verify(sample())
        self.assertEqual((p["frame"],p["guard_hits"],
                          p["previous_guard_hits"],p["shots"]),
                         (117,3,2,6))
    def test_forged_last_damage_and_provenance_rejected(self):
        raw=sample()
        mutants=[
            b"",raw[:-1],raw+raw,raw.replace(b"\n",b"\r\n"),
            raw.replace(b"FOURTH_GUARD_CLEAR",b"THIRD_GUARD_CLEAR",1),
            raw.replace(b"frame=117",b"frame=0",1),
            raw.replace(b"frame=117",b"frame=301",1),
            raw.replace(b"hero_x=16384",b"hero_x=0",1),
            raw.replace(b"hero_hp=5",b"hero_hp=4",1),
            raw.replace(b"guard_hp=0",b"guard_hp=1",1),
            raw.replace(b"previous_guard_hp=1",b"previous_guard_hp=2",1),
            raw.replace(b"guard_hits=3",b"guard_hits=2",1),
            raw.replace(b"previous_guard_hits=2",b"previous_guard_hits=1",1),
            raw.replace(b"guard_attacks=0",b"guard_attacks=1",1),
            raw.replace(b"shots=6",b"shots=2",1),
            raw.replace(b"sentry_hp=2",b"sentry_hp=1",1),
            raw.replace(b"wave=0",b"wave=1",1),
            raw.replace(b"clear=0",b"clear=1",1),
            raw.replace(b"dash=0",b"dash=1",1),
            raw.replace(b"input_fire=1",b"input_fire=0",1),
            raw.replace(b"source=live_guest",b"source=guest_script",1),
            raw.replace(b"original_game_proven=no",b"original_game_proven=yes",1),
        ]
        for n,item in enumerate(mutants):
            with self.subTest(index=n),self.assertRaises((ValueError,UnicodeError)):
                m.verify(item)
    def test_needs_prior_real_fourth_combat_and_host_x11(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            (base/"guest-fourth-guard-clear-witness.txt").write_bytes(sample())
            with self.assertRaisesRegex(ValueError,"first fourth-run"):
                m.audit(base)

if __name__=="__main__":
    unittest.main()
