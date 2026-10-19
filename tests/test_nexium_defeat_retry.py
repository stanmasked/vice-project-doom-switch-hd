"""Negative fixtures test strict native witness parser, not emulator behavior."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "live_defeat_retry",ROOT/"tools/audit_nexium_defeat_retry.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
def sample():
    return (
        "VPD_ROMFREE_DEFEAT_RETRY_V1 seq=1 event=contact frame=195 "
        "hero_x=50176 hero_hp=4 guard_hp=3 guard_attacks=1 "
        "sentry_hp=2 wave=0 clear=0 input_right=1 input_minus=0 "
        "old_frame=0 old_hp=0 source=live_guest original_game_proven=no\n"
        "VPD_ROMFREE_DEFEAT_RETRY_V1 seq=2 event=death frame=323 "
        "hero_x=50176 hero_hp=0 guard_hp=3 guard_attacks=5 "
        "sentry_hp=2 wave=0 clear=0 input_right=0 input_minus=0 "
        "old_frame=0 old_hp=0 source=live_guest original_game_proven=no\n"
        "VPD_ROMFREE_DEFEAT_RETRY_V1 seq=3 event=restart frame=0 "
        "hero_x=12288 hero_hp=5 guard_hp=3 guard_attacks=0 "
        "sentry_hp=2 wave=0 clear=0 input_right=0 input_minus=1 "
        "old_frame=332 old_hp=0 source=live_guest original_game_proven=no\n"
    ).encode("ascii")

class DefeatRetryAuditTests(unittest.TestCase):
    def test_genuine_melee_and_native_reset(self):
        self.assertEqual(m.verify(sample()),
            {"contact_frame":195,"death_frame":323,
             "restart_source_frame":332})
    def test_reject_impossible_melee_cadence(self):
        original=sample()
        # The exact accepted boundary is contact 195, death 323: four
        # real 32-frame cooldowns for the remaining four health points.
        for mutated in (
            original.replace(b"event=death frame=323",
                             b"event=death frame=322",1),
            original.replace(b"event=contact frame=195",
                             b"event=contact frame=196",1),
            original.replace(b"guard_attacks=5",
                             b"guard_attacks=6",1),
            original.replace(b"guard_attacks=5",
                             b"guard_attacks=50",1),
        ):
            with self.subTest(mutated=mutated),self.assertRaises(ValueError):
                m.verify(mutated)
        # A longer genuine wait between strikes is permitted.
        delayed=original.replace(b"event=death frame=323",
                                 b"event=death frame=324",1)
        self.assertEqual(m.verify(delayed)["death_frame"],324)
    def test_reject_order_provenance_health_and_control_forgeries(self):
        original=sample()
        rows=original.splitlines(keepends=True)
        cases=[
            b"",original[:-1],original+rows[-1],b"".join(reversed(rows)),
            original.replace(b"seq=1",b"seq=01",1),
            original.replace(b"event=death",b"event=contact"),
            original.replace(b"source=live_guest",b"source=guest_script",1),
            original.replace(b"original_game_proven=no",
                             b"original_game_proven=yes",1),
            original.replace(b"input_right=1",b"input_right=0",1),
            original.replace(b"guard_attacks=1",b"guard_attacks=0",1),
            original.replace(b"guard_attacks=5",b"guard_attacks=4",1),
            original.replace(b"hero_hp=0",b"hero_hp=1",1),
            original.replace(b"old_frame=332",b"old_frame=301"),
            original.replace(b"old_frame=332",b"old_frame=1000"),
            original.replace(b"hero_hp=5",b"hero_hp=4"),
            original.replace(b"hero_x=12288",b"hero_x=12300"),
            original.replace(b"input_minus=1",b"input_minus=0"),
            original.replace(b"sentry_hp=2",b"sentry_hp=0",1),
            original.replace(b"wave=0",b"wave=1",1),
            original.replace(b"\n",b"\r\n"),
        ]
        for i,changed in enumerate(cases):
            with self.subTest(case=i),self.assertRaises(
                (ValueError,UnicodeError)):
                m.verify(changed)
    def test_not_accepted_without_real_host_and_first_victory_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"guest-live-defeat-retry-witness.txt").write_bytes(sample())
            with self.assertRaisesRegex(ValueError,"X11 controller"):
                m.audit(root)
            (root/"input-probe.txt").write_text(
                "host_manual_retry_guest_observed=yes\n"
                "host_post_victory_guard_contact_sent=yes key=D observed=yes\n"
                "host_guard_death_observed=yes\n"
                "host_defeat_minus_key_sent=yes key=N expected=Minus\n"
                "host_defeat_retry_guest_observed=yes\n",encoding="ascii")
            with self.assertRaisesRegex(ValueError,"prior required"):
                m.audit(root)
if __name__=="__main__":
    unittest.main()
