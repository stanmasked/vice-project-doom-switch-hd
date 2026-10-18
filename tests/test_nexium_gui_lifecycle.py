"""Host lifecycle evidence is not guest cleanup or proof of Plus-caused GUI exit."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nexium_gui_lifecycle", ROOT / "tools/audit_nexium_gui_lifecycle.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def record(before="yes", after="yes", rc=124, outcome="watchdog"):
    return (
        f"target_window_before_plus={before}\n"
        f"target_window_visible_after_plus={after}\n"
        f"timeout_wrapper_wait_rc={rc}\n"
        f"host_process_outcome={outcome}\n"
    ).encode("ascii")


class HostLifecycleTests(unittest.TestCase):
    def test_watchdog_is_not_emulator_exit(self):
        self.assertEqual(mod.verify(record())["host_process_outcome"], "watchdog")
        self.assertEqual(mod.verify(record(after="no"))["host_process_outcome"],
                         "watchdog")

    def test_natural_return_cannot_be_attributed_to_plus(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "host-gui-lifecycle.txt").write_bytes(
                record(after="no", rc=0, outcome="returned_zero"))
            (root / "input-probe.txt").write_text(
                "host_manual_probe_sent=yes R+A/right/fire/jump/left\n"
                "host_plus_key_sent=yes\n")
            (root / "manual-result.txt").write_text(
                "VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS events=7\n")
            mod.audit(root)
            report = (root / "host-lifecycle-result.txt").read_text()
            self.assertIn("host_process_outcome=returned_zero", report)
            self.assertIn("emulator_gui_exit_caused_by_plus_proven=no", report)

    def test_guest_and_host_independence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "host-gui-lifecycle.txt").write_bytes(record())
            (root / "input-probe.txt").write_text(
                "host_manual_probe_sent=yes R+A/right/fire/jump/left\n"
                "host_plus_key_sent=yes\n")
            with self.assertRaisesRegex(ValueError, "proof missing"):
                mod.audit(root)
            (root / "manual-result.txt").write_text("INCONCLUSIVE\n")
            with self.assertRaisesRegex(ValueError, "not independently verified"):
                mod.audit(root)

    def test_broken_host_records_rejected(self):
        good = record()
        mutations = [
            b"", good[:-1], good + good, good.replace(b"\n", b"\r\n"),
            good.replace(b"\n", b"\x00\n"),
            good.replace(b"target_window_before_plus=yes",
                         b"target_window_before_plus=no"),
            good.replace(b"target_window_visible_after_plus=yes",
                         b"target_window_visible_after_plus=unknown"),
            good.replace(b"timeout_wrapper_wait_rc=124",
                         b"timeout_wrapper_wait_rc=0"),
            good.replace(b"timeout_wrapper_wait_rc=124",
                         b"timeout_wrapper_wait_rc=0124"),
            good.replace(b"timeout_wrapper_wait_rc=124",
                         b"timeout_wrapper_wait_rc=-1"),
            good.replace(b"host_process_outcome=watchdog",
                         b"host_process_outcome=returned_zero"),
            good.replace(b"host_process_outcome=watchdog",
                         b"host_process_outcome=unknown"),
            good.replace(b"target_window_before_plus=",
                         b"fake=1 target_window_before_plus="),
        ]
        for i, broken in enumerate(mutations):
            with self.subTest(i=i), self.assertRaises(
                (ValueError, UnicodeError)
            ):
                mod.verify(broken)


if __name__ == "__main__":
    unittest.main()
