"""Native witness parser mutations are not substitutes for NeXium input."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "live_defeat",ROOT/"tools/audit_nexium_guard_live_defeat.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def witness():
    return (
        "VPD_ROMFREE_GUARD_LIVE_DEFEAT_V1 seq=1 event=fire frame=188 "
        "player_x=52224 guard_x=57344 hp_before=2 hp_after=2 "
        "hits_before=1 hits_after=1 shots=2 input_fire=1 "
        "source=live_guest original_game_proven=no\n"
        "VPD_ROMFREE_GUARD_LIVE_DEFEAT_V1 seq=2 event=impact frame=190 "
        "player_x=52224 guard_x=57344 hp_before=2 hp_after=1 "
        "hits_before=1 hits_after=2 shots=2 input_fire=1 "
        "source=live_guest original_game_proven=no\n"
        "VPD_ROMFREE_GUARD_LIVE_DEFEAT_V1 seq=3 event=defeat frame=200 "
        "player_x=52224 guard_x=57344 hp_before=1 hp_after=0 "
        "hits_before=2 hits_after=3 shots=3 input_fire=1 "
        "source=live_guest original_game_proven=no\n"
    ).encode("ascii")


class LiveGuardDefeatAudit(unittest.TestCase):
    def test_realistic_two_hit_defeat_chain(self):
        self.assertEqual(mod.verify(witness()),{
            "fire_frame":188, "defeat_frame":200,
            "impacts":2, "start_hp":2,"final_hits":3
        })

    def test_missing_forged_or_unchained_transitions_fail(self):
        good=witness()
        rows=good.splitlines(keepends=True)
        broken=[
            b"",good[:-1],rows[0],rows[1],good+good,
            b"".join(reversed(rows)),good+rows[-1],
            good.replace(b"seq=1",b"seq=01",1),
            good.replace(b"event=defeat",b"event=impact"),
            good.replace(b"frame=190",b"frame=188"),
            good.replace(b"hp_after=0",b"hp_after=1"),
            good.replace(b"hp_before=1 hp_after=0",
                         b"hp_before=2 hp_after=0"),
            good.replace(b"hits_after=2 shots=2",
                         b"hits_after=1 shots=2"),
            good.replace(b"hits_before=2 hits_after=3",
                         b"hits_before=1 hits_after=3"),
            good.replace(b"hp_before=2 hp_after=2",
                         b"hp_before=3 hp_after=2"),
            good.replace(b"input_fire=1",b"input_fire=0",1),
            good.replace(b"shots=3",b"shots=0"),
            good.replace(b"source=live_guest",b"source=guest_script",1),
            good.replace(b"guard_x=57344",b"guard_x=50000",1),
            good.replace(b"player_x=52224",b"player_x=65536",1),
            good.replace(b"original_game_proven=no",
                         b"original_game_proven=yes",1),
            good.replace(b"\n",b"\r\n"),
            good.replace(b"\n",b"\x00\n"),
        ]
        for n,raw in enumerate(broken):
            with self.subTest(n=n),self.assertRaises(
                (ValueError,UnicodeError)
            ):
                mod.verify(raw)

    def test_real_guest_contact_must_precede_manual_fire(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"guest-guard-live-defeat-witness.txt").write_bytes(witness())
            (root/"input-probe.txt").write_text(
                "host_guard_live_fire_sent=yes key=Z after_guest_strike=yes\n")
            for name,prefix in (
                ("manual-result.txt","VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "),
                ("dash-result.txt","VPD_NEXIUM_GUEST_DASH_PASS "),
                ("guard-result.txt","VPD_NEXIUM_GUARD_PATROL_PASS "),
                ("guard-combat-result.txt","VPD_NEXIUM_GUARD_COMBAT_SCRIPT_PASS "),
                ("guard-live-result.txt","VPD_NEXIUM_GUARD_LIVE_CONTACT_PASS "),
                ("native-exit-result.txt","VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
            ):
                (root/name).write_text(prefix+"ok\n")
            with self.assertRaisesRegex(ValueError,"linked live"):
                mod.audit(root)
            (root/"guest-guard-live-witness.txt").write_text(
                "VPD_ROMFREE_GUARD_LIVE_V1 seq=1 event=alert frame=133 guard_hp=2\n"
                "VPD_ROMFREE_GUARD_LIVE_V1 seq=2 event=strike frame=186 guard_hp=2\n"
            )
            mod.audit(root)
            self.assertIn("VPD_NEXIUM_GUARD_LIVE_DEFEAT_PASS",
                          (root/"guard-live-defeat-result.txt").read_text())
            (root/"input-probe.txt").write_text("host_plus_key_sent=yes\n")
            with self.assertRaisesRegex(ValueError,"Fire trial"):
                mod.audit(root)
            (root/"input-probe.txt").write_text(
                "host_guard_live_fire_sent=yes key=Z after_guest_strike=yes\n")
            (root/"guest-guard-live-witness.txt").write_text(
                "VPD_ROMFREE_GUARD_LIVE_V1 seq=1 event=alert frame=190 guard_hp=2\n"
                "VPD_ROMFREE_GUARD_LIVE_V1 seq=2 event=strike frame=200 guard_hp=2\n"
            )
            with self.assertRaisesRegex(ValueError,"does not follow"):
                mod.audit(root)


if __name__=="__main__":
    unittest.main()
