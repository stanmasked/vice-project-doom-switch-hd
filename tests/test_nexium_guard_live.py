"""Synthetic mutations of the live NRO observer; not an emulator proof."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "live_guard",ROOT/"tools/audit_nexium_guard_live.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def witness():
    return (
        "VPD_ROMFREE_GUARD_LIVE_V1 seq=1 event=alert frame=63 "
        "player_x=44544 guard_x=81408 player_hp=5 guard_hp=3 "
        "attacks=0 cooldown=0 alerted=1 input_right=1 "
        "source=live_guest original_game_proven=no\n"
        "VPD_ROMFREE_GUARD_LIVE_V1 seq=2 event=strike frame=104 "
        "player_x=65536 guard_x=61440 player_hp=4 guard_hp=3 "
        "attacks=1 cooldown=32 alerted=1 input_right=1 "
        "source=live_guest original_game_proven=no\n"
    ).encode("ascii")

class NativeLiveGuardTests(unittest.TestCase):
    def test_two_real_contact_transitions(self):
        self.assertEqual(mod.verify(witness()),{
            "alert_frame":63,"strike_frame":104
        })
    def test_fails_on_modified_or_host_forged_evidence(self):
        ok=witness()
        lines=ok.splitlines(keepends=True)
        cases=[
            b"",ok[:-1],lines[0],lines[1],ok+ok,
            b"".join(reversed(lines)),
            ok.replace(b"seq=1",b"seq=01",1),
            ok.replace(b"frame=104",b"frame=62",1),
            ok.replace(b"player_hp=4",b"player_hp=5",1),
            ok.replace(b"cooldown=32",b"cooldown=31",1),
            ok.replace(b"attacks=1",b"attacks=0",1),
            ok.replace(b"guard_hp=3",b"guard_hp=2",1),
            ok.replace(b"input_right=1",b"input_right=0",1),
            ok.replace(b"source=live_guest",b"source=guest_script",1),
            ok.replace(b"original_game_proven=no",
                       b"original_game_proven=yes",1),
            ok.replace(b"player_x=65536",b"player_x=9999999",1),
            ok.replace(b"guard_x=81408",b"guard_x=81409",1),
            ok.replace(b"guard_x=61440",b"guard_x=90000",1),
            ok.replace(b"\n",b"\r\n"),
            ok.replace(b"\n",b"\x00\n"),
        ]
        for n,bad in enumerate(cases):
            with self.subTest(n=n),self.assertRaises(
                (ValueError,UnicodeError)
            ):
                mod.verify(bad)
    def test_requires_host_input_and_all_prior_native_audits(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            (root/"guest-guard-live-witness.txt").write_bytes(witness())
            with self.assertRaisesRegex(ValueError,"right-direction"):
                mod.audit(root)
            (root/"input-probe.txt").write_text(
                "host_guard_live_move_sent=yes key=D duration=3.4s\n")
            for file,header in (
                ("manual-result.txt","VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "),
                ("dash-result.txt","VPD_NEXIUM_GUEST_DASH_PASS "),
                ("guard-result.txt","VPD_NEXIUM_GUARD_PATROL_PASS "),
                ("guard-combat-result.txt","VPD_NEXIUM_GUARD_COMBAT_SCRIPT_PASS "),
                ("native-exit-result.txt","VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
            ):
                (root/file).write_text(header+"ok\n")
            mod.audit(root)
            self.assertIn("VPD_NEXIUM_GUARD_LIVE_CONTACT_PASS",
                          (root/"guard-live-result.txt").read_text())
            (root/"guard-combat-result.txt").write_text("INCONCLUSIVE\n")
            with self.assertRaisesRegex(ValueError,"independent"):
                mod.audit(root)

if __name__=="__main__":
    unittest.main()
