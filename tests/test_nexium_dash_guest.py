"""Synthetic parser cases never stand in for real NeXium guest evidence."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "dash_guest_audit", ROOT / "tools/audit_nexium_dash_guest.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def witness():
    return (
        "VPD_ROMFREE_DASH_V1 seq=1 event=start frame=120 "
        "delta_fixed=1536 cooldown=45 source=ZR+Right "
        "mode=manual original_game_proven=no\n"
        "VPD_ROMFREE_DASH_V1 seq=2 event=complete frame=125 "
        "delta_fixed=9216 cooldown=40 source=ZR+Right "
        "mode=manual original_game_proven=no\n"
    ).encode("ascii")


class NeXiumDashGuestAudit(unittest.TestCase):
    def test_two_actual_dash_events_expected(self):
        self.assertEqual(audit.verify(witness()), {
            "start_frame": 120, "complete_frame": 125
        })

    def test_missing_reordered_or_forged_guest_data_rejected(self):
        good = witness()
        lines = good.splitlines(keepends=True)
        cases = [
            b"", good[:-1], good + good, lines[0], lines[1],
            b"".join(reversed(lines)),
            good.replace(b"seq=1", b"seq=01"),
            good.replace(b"frame=125", b"frame=126"),
            good.replace(b"frame=120", b"frame=9999"),
            good.replace(b"delta_fixed=1536", b"delta_fixed=512"),
            good.replace(b"delta_fixed=9216", b"delta_fixed=8192"),
            good.replace(b"cooldown=45", b"cooldown=44"),
            good.replace(b"cooldown=40", b"cooldown=39"),
            good.replace(b"source=ZR+Right", b"source=host", 1),
            good.replace(b"mode=manual", b"mode=demo", 1),
            good.replace(b"original_game_proven=no",
                         b"original_game_proven=yes", 1),
            good.replace(b"\n", b"\r\n"),
            good.replace(b"\n", b"\x00\n"),
            good.replace(b"seq=2 event=complete",
                         b"event=complete seq=2"),
        ]
        for n, bad in enumerate(cases):
            with self.subTest(n=n), self.assertRaises(
                (ValueError, UnicodeError)
            ):
                audit.verify(bad)

    def test_host_keys_alone_do_not_count(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "input-probe.txt").write_text(
                "host_dash_probe_sent=yes keys=D+T expected=ZR+Right\n")
            (root / "manual-result.txt").write_text(
                "VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS events=7\n")
            (root / "native-exit-result.txt").write_text(
                "VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS guest_exit_code=0\n")
            with self.assertRaisesRegex(ValueError, "guest-created"):
                audit.audit(root)
            (root / "guest-dash-witness.txt").write_bytes(witness())
            audit.audit(root)
            self.assertIn("VPD_NEXIUM_GUEST_DASH_PASS",
                          (root / "dash-result.txt").read_text())
            (root / "input-probe.txt").write_text(
                "host_manual_probe_sent=yes\n")
            with self.assertRaisesRegex(ValueError, "host ZR"):
                audit.audit(root)
            (root / "input-probe.txt").write_text(
                "host_dash_probe_sent=yes keys=D+T expected=ZR+Right\n")
            (root / "native-exit-result.txt").write_text(
                "INCONCLUSIVE: no guest process exit\n")
            with self.assertRaisesRegex(ValueError, "independent"):
                audit.audit(root)


if __name__ == "__main__":
    unittest.main()
