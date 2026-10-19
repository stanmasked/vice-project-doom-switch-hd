"""Negative native-source guard-clear audit fixtures, not NeXium proof."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "third_guard_clear",ROOT/"tools/audit_nexium_third_guard_clear.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def valid():
    return (
        b"VPD_ROMFREE_THIRD_GUARD_CLEAR_V1 event=guard_clear frame=110 "
        b"hero_x=16896 hero_hp=5 guard_hp=0 previous_guard_hp=1 "
        b"guard_hits=3 previous_guard_hits=2 guard_attacks=0 shots=6 "
        b"sentry_hp=2 wave=0 clear=0 dash=0 input_fire=1 "
        b"source=live_guest original_game_proven=no\n"
    )

class ThirdGuardClearTests(unittest.TestCase):
    def test_accept_true_final_guard_hit(self):
        result=m.verify(valid())
        self.assertEqual((result["frame"],result["guard_hits"],
                          result["previous_guard_hits"],result["shots"]),
                         (110,3,2,6))
    def test_reject_fake_guard_clears(self):
        raw=valid()
        cases=[
            b"",raw[:-1],raw+raw,raw.replace(b"\n",b"\r\n"),
            raw.replace(b"frame=110",b"frame=0",1),
            raw.replace(b"frame=110",b"frame=301",1),
            raw.replace(b"hero_x=16896",b"hero_x=12",1),
            raw.replace(b"hero_hp=5",b"hero_hp=4",1),
            raw.replace(b"guard_hp=0",b"guard_hp=1",1),
            raw.replace(b"previous_guard_hp=1",b"previous_guard_hp=2",1),
            raw.replace(b"guard_hits=3",b"guard_hits=2",1),
            raw.replace(b"previous_guard_hits=2",
                        b"previous_guard_hits=1",1),
            raw.replace(b"guard_attacks=0",b"guard_attacks=1",1),
            raw.replace(b"shots=6",b"shots=2",1),
            raw.replace(b"shots=6",b"shots=16",1),
            raw.replace(b"sentry_hp=2",b"sentry_hp=1",1),
            raw.replace(b"wave=0",b"wave=1",1),
            raw.replace(b"clear=0",b"clear=1",1),
            raw.replace(b"dash=0",b"dash=1",1),
            raw.replace(b"input_fire=1",b"input_fire=0",1),
            raw.replace(b"source=live_guest",b"source=guest_script",1),
            raw.replace(b"original_game_proven=no",
                        b"original_game_proven=yes",1),
        ]
        for index,data in enumerate(cases):
            with self.subTest(index=index),self.assertRaises(
                    (ValueError,UnicodeError)):
                m.verify(data)
    def test_requires_first_real_hit_x11_and_actual_pad_fire(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            (base/"guest-third-guard-clear-witness.txt").write_bytes(valid())
            with self.assertRaisesRegex(ValueError,"initial third-run"):
                m.audit(base)

if __name__=="__main__":
    unittest.main()
