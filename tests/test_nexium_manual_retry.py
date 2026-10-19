"""Mutations against native real-Minus stage-replay proof, not mock emulator."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "manual_retry_audit",ROOT/"tools/audit_nexium_manual_retry.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def valid():
    return (
        "VPD_ROMFREE_MANUAL_RETRY_V1 event=restart reason=victory "
        "old_frame=596 old_hp=3 old_guard_hp=0 old_sentry_hp=0 "
        "old_clear=1 new_frame=0 new_x=12288 new_hp=5 "
        "new_guard_hp=3 new_sentry_hp=2 wave=0 clear=0 input_minus=1 "
        "source=live_guest original_game_proven=no\n"
    ).encode("ascii")

class ManualRetryNeXiumAuditTests(unittest.TestCase):
    def test_realistic_guest_source_state_reset(self):
        obs=m.parse_guest(valid())
        self.assertEqual(obs["old_frame"],596)
        self.assertEqual(obs["new_hp"],5)
        self.assertEqual(obs["input_minus"],1)

    def test_forged_key_source_or_broken_progress_rejected(self):
        good=valid()
        cases=[
            b"", good[:-1],good+good, good.replace(b"\n",b"\r\n"),
            good.replace(b"source=live_guest",b"source=host_script"),
            good.replace(b"reason=victory",b"reason=defeat"),
            good.replace(b"old_clear=1",b"old_clear=0"),
            good.replace(b"old_guard_hp=0",b"old_guard_hp=3"),
            good.replace(b"old_sentry_hp=0",b"old_sentry_hp=1"),
            good.replace(b"new_frame=0",b"new_frame=1"),
            good.replace(b"new_x=12288",b"new_x=8192"),
            good.replace(b"new_hp=5",b"new_hp=4"),
            good.replace(b"new_guard_hp=3",b"new_guard_hp=0"),
            good.replace(b"new_sentry_hp=2",b"new_sentry_hp=0"),
            good.replace(b"wave=0",b"wave=1"),
            good.replace(b"clear=0",b"clear=1"),
            good.replace(b"input_minus=1",b"input_minus=0"),
            good.replace(b"original_game_proven=no",
                         b"original_game_proven=yes"),
            good.replace(b"old_frame=596",b"old_frame=0596"),
            good.replace(b"old_hp=3",b"old_hp=0"),
        ]
        for i,broken in enumerate(cases):
            with self.subTest(case=i),self.assertRaises(
                (ValueError,UnicodeError)
            ):
                m.parse_guest(broken)

    def test_guest_alone_is_not_a_native_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"guest-manual-retry-witness.txt").write_bytes(valid())
            with self.assertRaisesRegex(ValueError,"X11 input"):
                m.audit(root)
            (root/"input-probe.txt").write_text(
                "host_manual_retry_key_sent=yes key=N expected=Minus\n"
                "host_manual_retry_guest_observed=yes\n")
            with self.assertRaisesRegex(ValueError,"actual NeXium Minus"):
                m.audit(root)
            (root/"input-probe.txt").write_text(
                "host_second_wave_controls_sent=yes keys=D+Z guest_exit=yes\n"
                "host_manual_retry_key_sent=yes key=N expected=Minus\n"
                "host_manual_retry_guest_observed=yes\n")
            with self.assertRaisesRegex(ValueError,"mandatory native"):
                m.audit(root)

if __name__=="__main__":
    unittest.main()
