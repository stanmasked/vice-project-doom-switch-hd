"""Native NeXium kernel/runner exit evidence, separate from the GUI lifecycle."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "native_exit", ROOT / "tools/audit_nexium_guest_process_exit.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sample_log():
    return (
        "[20:54:09.416] [ INFO] [nexium_kernel::boot] Loading NRO from: /runner/vpd_native_scene.nro\n"
        "[20:54:09.540] [ INFO] [nexium_runner::boot] Starting emulation loop\n"
        "[20:54:32.561] [ INFO] [nexium_kernel::kernel::svc] svcExitProcess - terminating process (x0=0x0 lr=0x1000162cc)\n"
        "[20:54:32.561] [ INFO] [nexium_runner::boot] Process exited\n"
        "[20:54:32.561] [ INFO] [nexium_runner::boot] Emulation complete: 19267000000 cycles, 3166 SVCs\n"
        "[20:54:32.563] [ INFO] [nexium_runner::boot] [core2] stopped\n"
        "[20:54:32.563] [ INFO] [nexium_runner::boot] [core1] stopped\n"
        "[20:54:32.563] [ INFO] [nexium_runner::boot] [core3] stopped\n"
    ).encode("utf-8")


class NativeGuestExitTests(unittest.TestCase):
    def test_realistic_successful_guest_exit(self):
        result = mod.verify_log(sample_log())
        self.assertEqual(result["guest_return_code"], 0)
        self.assertEqual(result["cycles"], 19267000000)
        self.assertEqual(result["svc_calls"], 3166)
        self.assertEqual(result["core_stops"], 3)

    def test_wrong_status_missing_stop_or_reordered_events_fail(self):
        good = sample_log()
        lines = good.splitlines(keepends=True)
        bad = [
            b"", good[:-1], good + good,
            good.replace(b"vpd_native_scene.nro", b"other.nro"),
            good.replace(b"x0=0x0", b"x0=0x1"),
            good.replace(b"19267000000 cycles", b"0 cycles"),
            good.replace(b"3166 SVCs", b"0 SVCs"),
            good.replace(b"[core3] stopped", b"[core4] stopped"),
            good.replace(b"[core3] stopped", b"[core2] stopped"),
            good.replace(b"svcExitProcess - terminating process ", b"svcExitProcess - failed "),
            good.replace(b"[nexium_runner::boot] Process exited",
                         b"[unknown::boot] Process exited"),
            b"".join(lines[:2] + [lines[3], lines[2]] + lines[4:]),
            b"".join(lines[:4] + lines[5:]),
            good.replace(b"[nexium_kernel::boot] Loading NRO from:",
                         b"[nexium_runner::boot] Loading NRO from:"),
            good.replace(b"[20:54:32.561] [ INFO] [nexium_kernel::kernel::svc]",
                         b"[20:54:32.561] [ WARN] [nexium_kernel::kernel::svc]"),
        ]
        for i, corrupted in enumerate(bad):
            with self.subTest(index=i), self.assertRaises(
                (ValueError, UnicodeError)
            ):
                mod.verify_log(corrupted)

    def test_requires_real_log_and_other_independent_audits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_dir = root / "xdg-config" / "NeXium" / "logs"
            log_dir.mkdir(parents=True)
            (root / "guest-manual-witness.txt").write_text("guest")
            (root / "manual-result.txt").write_text(
                "VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS events=7\n")
            (root / "host-lifecycle-result.txt").write_text(
                "VPD_NEXIUM_HOST_LIFECYCLE_CLASSIFIED target_window_after_plus=yes\n")
            with self.assertRaisesRegex(ValueError, "exactly one"):
                mod.audit(root)
            logfile = log_dir / "nexium-20261018-205408.log"
            logfile.write_bytes(sample_log())
            (root / "host-lifecycle-result.txt").write_text("INCONCLUSIVE\n")
            with self.assertRaisesRegex(ValueError, "GUI lifecycle"):
                mod.audit(root)
            (root / "host-lifecycle-result.txt").write_text(
                "VPD_NEXIUM_HOST_LIFECYCLE_CLASSIFIED target_window_after_plus=yes\n")
            mod.audit(root)
            report = (root / "native-exit-result.txt").read_text()
            self.assertIn("guest_exit_code=0", report)
            self.assertIn("gui_process_exit_proven=no", report)
            (log_dir / "nexium-stale.log").write_bytes(sample_log())
            with self.assertRaisesRegex(ValueError, "exactly one"):
                mod.audit(root)


if __name__ == "__main__":
    unittest.main()
