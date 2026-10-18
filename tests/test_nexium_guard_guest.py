"""Host fixtures are not NeXium proof; strict mutation tests only."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "guard_guest", ROOT/"tools/audit_nexium_guard_guest.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def valid():
    return (
        "VPD_ROMFREE_GUARD_V1 seq=1 event=first frame=1 "
        "x_fixed=65792 hp=3 alerted=0 source=guest original_game_proven=no\n"
        "VPD_ROMFREE_GUARD_V1 seq=2 event=patrol frame=8 "
        "x_fixed=67584 hp=3 alerted=0 source=guest original_game_proven=no\n"
    ).encode("ascii")

class GuardGuestTests(unittest.TestCase):
    def test_milestones(self):
        self.assertEqual(mod.verify(valid()),{"first_frame":1,"patrol_frame":8})

    def test_corrupt_or_forged_records_fail(self):
        good=valid()
        rows=good.splitlines(keepends=True)
        mutations=[
            b"",good[:-1],rows[0],rows[1],good+good,
            b"".join(reversed(rows)),
            good.replace(b"frame=1",b"frame=0"),
            good.replace(b"frame=8",b"frame=9"),
            good.replace(b"seq=1",b"seq=01"),
            good.replace(b"hp=3",b"hp=2"),
            good.replace(b"alerted=0",b"alerted=1"),
            good.replace(b"x_fixed=65792",b"x_fixed=66048"),
            good.replace(b"x_fixed=67584",b"x_fixed=67583"),
            good.replace(b"source=guest",b"source=host"),
            good.replace(b"original_game_proven=no",
                         b"original_game_proven=yes"),
            good.replace(b"\n",b"\r\n"),
            good.replace(b"\n",b"\x00\n"),
            good.replace(b"seq=2 event=patrol",b"event=patrol seq=2"),
        ]
        for n,broken in enumerate(mutations):
            with self.subTest(n=n),self.assertRaises(
                (ValueError,UnicodeError)
            ):
                mod.verify(broken)

    def test_requires_other_real_guest_proofs(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            for filename,marker in (
                ("manual-result.txt","VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "),
                ("native-exit-result.txt","VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
                ("dash-result.txt","VPD_NEXIUM_GUEST_DASH_PASS "),
            ):
                (root/filename).write_text(marker+"ok\n")
            with self.assertRaisesRegex(ValueError,"SD evidence"):
                mod.audit(root)
            (root/"guest-guard-witness.txt").write_bytes(valid())
            mod.audit(root)
            self.assertIn("VPD_NEXIUM_GUARD_PATROL_PASS",
                          (root/"guard-result.txt").read_text())
            (root/"dash-result.txt").write_text("INCONCLUSIVE\n")
            with self.assertRaisesRegex(ValueError,"independent"):
                mod.audit(root)

if __name__=="__main__":
    unittest.main()
