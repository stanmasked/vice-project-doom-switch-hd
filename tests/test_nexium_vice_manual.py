"""Synthetic tests of strict parser: fixtures are never accepted as runtime proof."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("manual",
 ROOT/"tools/audit_nexium_vice_manual.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

EVENTS=mod.EVENTS
def data():
    lines=[]
    for seq,name in enumerate(EVENTS,1):
        frame=0 if seq==1 else seq*15
        lines.append(
            f"VPD_ROMFREE_MANUAL_V1 seq={seq} event={name} "
            f"frame={frame} metric=1 mode=manual original_game_proven=no"
        )
    return ("\n".join(lines)+"\n").encode()

class GuestManualWitnessTests(unittest.TestCase):
    def test_bounded_valid_sequence(self):
        self.assertEqual(mod.verify(data())["events"],7)

    def test_wrong_events_cannot_be_certified(self):
        fixture=data()
        changes=[
            b"",fixture[:-1],fixture+fixture,
            fixture.replace(b"event=right",b"event=left",1),
            fixture.replace(b"seq=4",b"seq=04",1),
            fixture.replace(b"frame=30",b"frame=0",1),
            fixture.replace(b"metric=1",b"metric=0",1),
            fixture.replace(b"mode=manual",b"mode=demo",1),
            fixture.replace(b"original_game_proven=no",
                            b"original_game_proven=yes",1),
            fixture.replace(b"event=plus",b"event=fire",1),
            fixture.replace(b"event=exit",b"event=plus",1),
            fixture.replace(b"\n",b"\r\n"),
            fixture.replace(b"\n",b"\x00\n"),
            fixture.replace(b"frame=45",b"frame=999999",1),
        ]
        for i,bad in enumerate(changes):
            with self.subTest(case=i),self.assertRaises(
                (ValueError, UnicodeError)
            ):
                mod.verify(bad)

    def test_only_real_guest_file_and_host_input_log_can_pass(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            (root/"input-probe.txt").write_text(
                "host_manual_probe_sent=yes\nhost_plus_key_sent=yes\n")
            with self.assertRaisesRegex(ValueError,"guest-created"):
                mod.audit(root)
            (root/"guest-manual-witness.txt").write_bytes(data())
            mod.audit(root)
            (root/"input-probe.txt").write_text("host_plus_key_sent=yes\n")
            with self.assertRaisesRegex(ValueError,"injection"):
                mod.audit(root)

if __name__=="__main__":
    unittest.main()
