"""Source-driven hostile bullet: strict format, mutations and external X11 gate."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "hostile_halo_audit",ROOT/"tools/audit_nexium_hd_hostile_halo.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

def witness():
    return (
        b"VPD_ROMFREE_HOSTILE_HALO_V1 event=fourth_turret_bullet "
        b"frame=350 bullet_slot=0 bullet_x=159744 bullet_y=55552 "
        b"bullet_age=3 bullet_vx=-768 "
        b"sentry_hp=1 sentry_shots=1 guard_hp=0 wave=1 clear=0 "
        b"hero_hp=5 samples=1024 changed=14 "
        b"unlit_hash=0123456789abcdef lit_hash=fedcba9876543210 "
        b"same_guest_frame=yes native_framebuffer=yes "
        b"source=live_guest original_game_proven=no\n")
class HostileHaloAuditTests(unittest.TestCase):
    def test_valid_native_source_format(self):
        row=audit.verify(witness())
        self.assertEqual(row["frame"],350)
        self.assertEqual(row["bullet_vx"],-768)
        self.assertEqual(row["changed"],14)
        self.assertNotEqual(row["unlit_hash"],row["lit_hash"])

    def test_mutation_rejection(self):
        record=witness()
        altered=[
            b"",record[:-1],record+record,
            record.replace(b"\n",b"\r\n"),
            record.replace(b"frame=350",b"frame=0"),
            record.replace(b"frame=350",b"frame=1201"),
            record.replace(b"bullet_slot=0",b"bullet_slot=3"),
            record.replace(b"bullet_x=159744",b"bullet_x=99999999"),
            record.replace(b"bullet_y=55552",b"bullet_y=999999"),
            record.replace(b"bullet_age=3",b"bullet_age=90"),
            record.replace(b"bullet_vx=-768",b"bullet_vx=0"),
            record.replace(b"sentry_hp=1",b"sentry_hp=0"),
            record.replace(b"sentry_shots=1",b"sentry_shots=0"),
            record.replace(b"guard_hp=0",b"guard_hp=3"),
            record.replace(b"hero_hp=5",b"hero_hp=0"),
            record.replace(b"clear=0",b"clear=1"),
            record.replace(b"samples=1024",b"samples=25"),
            record.replace(b"changed=14",b"changed=2"),
            record.replace(b"changed=14",b"changed=1025"),
            record.replace(b"unlit_hash=0123456789abcdef",
                           b"unlit_hash=fedcba9876543210"),
            record.replace(b"same_guest_frame=yes",
                           b"same_guest_frame=no"),
            record.replace(b"native_framebuffer=yes",
                           b"native_framebuffer=no"),
            record.replace(b"source=live_guest",
                           b"source=synthetic_fixture"),
            record.replace(b"original_game_proven=no",
                           b"original_game_proven=yes"),
        ]
        for i,bad in enumerate(altered):
            with self.subTest(case=i):
                with self.assertRaises((ValueError,UnicodeError)):
                    audit.verify(bad)

    def test_real_fourth_stage_and_x11_mandatory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            with self.assertRaisesRegex(ValueError,"live guest hostile"):
                audit.audit(path)
            (path/"guest-hd-hostile-halo-witness.txt").write_bytes(witness())
            with self.assertRaisesRegex(ValueError,"independent fourth"):
                audit.audit(path)
            # No guessed stage or synthetic X11 substitute is accepted.
            (path/"guest-fourth-stage-witness.txt").write_bytes(b"not a trace")
            with self.assertRaises(ValueError):
                audit.audit(path)
if __name__=="__main__":
    unittest.main()
