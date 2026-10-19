"""Reject forged or unrelated native grounded dust evidence."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "hd_footstep",ROOT/"tools/audit_nexium_hd_footstep.py")
a=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

def sample():
    return (
        b"VPD_ROMFREE_HD_FOOTSTEP_V1 event=fourth_ground_move "
        b"frame=20 hero_x=16384 hero_vx=512 grounded=1 "
        b"hero_hp=5 guard_hp=3 shots=0 wave=0 clear=0 "
        b"samples=1056 changed=14 "
        b"no_dust_hash=0123456789abcdef dust_hash=fedcba9876543210 "
        b"same_guest_frame=yes native_framebuffer=yes "
        b"source=live_guest original_game_proven=no\n")
class FootstepProofTests(unittest.TestCase):
    def test_canonical_event(self):
        self.assertEqual(a.verify(sample()),{
            "frame":20,"x":16384,"changed":14,
            "no_dust_hash":"0123456789abcdef",
            "dust_hash":"fedcba9876543210"})

    def test_mutation_rejection(self):
        good=sample()
        mutations=[
            b"",good[:-1],good+good,good.replace(b"\n",b"\r\n"),
            good.replace(b"frame=20",b"frame=00"),
            good.replace(b"frame=20",b"frame=101"),
            good.replace(b"hero_x=16384",b"hero_x=20"),
            good.replace(b"hero_vx=512",b"hero_vx=0"),
            good.replace(b"grounded=1",b"grounded=0"),
            good.replace(b"hero_hp=5",b"hero_hp=0"),
            good.replace(b"guard_hp=3",b"guard_hp=2"),
            good.replace(b"shots=0",b"shots=1"),
            good.replace(b"wave=0",b"wave=1"),
            good.replace(b"samples=1056",b"samples=25"),
            good.replace(b"changed=14",b"changed=2"),
            good.replace(b"changed=14",b"changed=1057"),
            good.replace(b"no_dust_hash=0123456789abcdef",
                         b"no_dust_hash=fedcba9876543210"),
            good.replace(b"same_guest_frame=yes",b"same_guest_frame=no"),
            good.replace(b"native_framebuffer=yes",b"native_framebuffer=no"),
            good.replace(b"source=live_guest",b"source=synthetic_host"),
            good.replace(b"original_game_proven=no",
                         b"original_game_proven=yes"),
        ]
        for index,bad in enumerate(mutations):
            with self.subTest(index=index),self.assertRaises((ValueError,UnicodeError)):
                a.verify(bad)

    def test_audit_requires_external_real_right_and_x11(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            (directory/"guest-hd-footstep-witness.txt").write_bytes(sample())
            with self.assertRaisesRegex(ValueError,"fourth-run guest reset"):
                a.audit(directory)
            (directory/"guest-fourth-retry-witness.txt").write_bytes(
                b"VPD_ROMFREE_FOURTH_RETRY_V1 seq=1 event=restart "
                b"old_frame=540 old_hp=5 old_guard_hp=0 old_sentry_hp=0 "
                b"old_clear=1 new_frame=0 new_x=12288 hero_hp=5 guard_hp=3 "
                b"sentry_hp=2 wave=0 clear=0 input_minus=1 "
                b"source=live_guest original_game_proven=no\n"
                b"VPD_ROMFREE_FOURTH_RETRY_V1 seq=2 event=move "
                b"frame=20 before_frame=19 before_x=15872 after_x=16384 "
                b"delta_fixed=512 hero_hp=5 guard_hp=3 sentry_hp=2 "
                b"guard_attacks=0 shots=0 wave=0 clear=0 input_right=1 "
                b"source=live_guest original_game_proven=no\n")
            with self.assertRaisesRegex(ValueError,"physical Minus/Right"):
                a.audit(directory)
            (directory/"fourth-retry-result.txt").write_text(
                "VPD_NEXIUM_FOURTH_RETRY_PASS verified\n",encoding="ascii")
            with self.assertRaisesRegex(ValueError,"screenshots not confirmed"):
                a.audit(directory)
if __name__=="__main__":
    unittest.main()
