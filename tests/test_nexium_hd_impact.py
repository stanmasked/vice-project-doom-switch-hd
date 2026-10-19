"""Fail closed on forged lit/unlit frame samples and missing real source."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "hd_hit",ROOT/"tools/audit_nexium_hd_impact.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
def valid():
    return (
        b"VPD_ROMFREE_HD_HIT_LIGHT_V1 event=source_guard_impact "
        b"frame=70 guard_hp=2 guard_hits=1 guard_flash=11 "
        b"hero_hp=5 shots=1 sentry_hp=2 wave=0 clear=0 "
        b"samples=25 changed=21 "
        b"unlit_hash=0123456789abcdef lit_hash=fedcba9876543210 "
        b"same_simulation_frame=yes native_framebuffer=yes "
        b"source=live_guest original_game_proven=no\n"
    )
class NativeHitLightEvidenceTests(unittest.TestCase):
    def test_valid_sample_proof(self):
        self.assertEqual(audit.verify(valid()),{
            "frame":70,"flash":11,"changed":21,
            "unlit_hash":"0123456789abcdef",
            "lit_hash":"fedcba9876543210"})

    def test_reject_forged_frameboard_and_damage(self):
        good=valid()
        bad=[
            b"",good[:-1],good+good,
            good.replace(b"\n",b"\r\n"),
            good.replace(b"frame=70",b"frame=0"),
            good.replace(b"guard_hp=2",b"guard_hp=3"),
            good.replace(b"guard_hits=1",b"guard_hits=2"),
            good.replace(b"guard_flash=11",b"guard_flash=0"),
            good.replace(b"guard_flash=11",b"guard_flash=20"),
            good.replace(b"hero_hp=5",b"hero_hp=4"),
            good.replace(b"shots=1",b"shots=2"),
            good.replace(b"sentry_hp=2",b"sentry_hp=1"),
            good.replace(b"wave=0",b"wave=1"),
            good.replace(b"clear=0",b"clear=1"),
            good.replace(b"samples=25",b"samples=24"),
            good.replace(b"changed=21",b"changed=0"),
            good.replace(b"changed=21",b"changed=2"),
            good.replace(b"changed=21",b"changed=26"),
            good.replace(b"unlit_hash=0123456789abcdef",
                         b"unlit_hash=fedcba9876543210"),
            good.replace(b"same_simulation_frame=yes",
                         b"same_simulation_frame=no"),
            good.replace(b"native_framebuffer=yes",
                         b"native_framebuffer=no"),
            good.replace(b"source=live_guest",b"source=host_synthetic"),
            good.replace(b"original_game_proven=no",
                         b"original_game_proven=yes"),
        ]
        for i,item in enumerate(bad):
            with self.subTest(index=i),self.assertRaises((ValueError,UnicodeError)):
                audit.verify(item)

    def test_fails_without_original_guest_hit_or_x11(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"guest-hd-hit-light-witness.txt").write_bytes(valid())
            with self.assertRaisesRegex(ValueError,"physical fourth-run Fire"):
                audit.audit(root)
            (root/"guest-fourth-combat-witness.txt").write_bytes(
                b"VPD_ROMFREE_FOURTH_COMBAT_V1 seq=1 event=fire frame=29 "
                b"hero_x=16896 hero_hp=5 guard_hp=3 guard_hits=0 "
                b"guard_attacks=0 shots=1 sentry_hp=2 wave=0 clear=0 dash=0 "
                b"input_fire=1 source=live_guest original_game_proven=no\n"
                b"VPD_ROMFREE_FOURTH_COMBAT_V1 seq=2 event=impact frame=68 "
                b"hero_x=16896 hero_hp=5 guard_hp=2 guard_hits=1 "
                b"guard_attacks=0 shots=1 sentry_hp=2 wave=0 clear=0 dash=0 "
                b"input_fire=0 source=live_guest original_game_proven=no\n")
            with self.assertRaisesRegex(ValueError,"physical X11"):
                audit.audit(root)

if __name__=="__main__":
    unittest.main()
