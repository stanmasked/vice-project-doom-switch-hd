#!/usr/bin/env python3
"""Classify host NeXium process/window observations without confusing them with guest exit.

This is host-side diagnostic evidence only. It cannot attest to the reason the
guest stopped, prove that Plus caused GUI termination, or replace guest records.
"""
import argparse
from pathlib import Path

FIELDS = (
    "target_window_before_plus",
    "target_window_visible_after_plus",
    "timeout_wrapper_wait_rc",
    "host_process_outcome",
)
OUTCOMES = {"returned_zero", "returned_nonzero", "watchdog",
            "signal_or_watchdog"}


def verify(raw):
    if not isinstance(raw, bytes) or not raw or len(raw) > 512:
        raise ValueError("host lifecycle data missing or oversized")
    text = raw.decode("ascii")
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise ValueError("malformed host lifecycle line endings")
    lines = text.splitlines()
    if len(lines) != len(FIELDS):
        raise ValueError("wrong number of host lifecycle records")
    values = {}
    for key, line in zip(FIELDS, lines):
        if not line.startswith(key + "=") or line.count("=") != 1:
            raise ValueError("unexpected lifecycle schema or field order")
        values[key] = line.split("=", 1)[1]
    before = values["target_window_before_plus"]
    after = values["target_window_visible_after_plus"]
    outcome = values["host_process_outcome"]
    raw_rc = values["timeout_wrapper_wait_rc"]
    if before not in ("yes", "no") or after not in ("yes", "no", "unknown"):
        raise ValueError("invalid X11 window observation")
    if (before == "no" and after != "unknown") or (
        before == "yes" and after == "unknown"
    ):
        raise ValueError("X11 observation contradicts tracked target window")
    if not raw_rc.isascii() or not raw_rc.isdecimal() or (
        len(raw_rc) > 1 and raw_rc[0] == "0"
    ):
        raise ValueError("noncanonical timeout wait status")
    rc = int(raw_rc)
    if rc > 255 or outcome not in OUTCOMES:
        raise ValueError("invalid host termination status")
    expected = ("returned_zero" if rc == 0 else "watchdog" if rc == 124
                else "signal_or_watchdog" if rc == 137
                else "returned_nonzero")
    if outcome != expected:
        raise ValueError("host process outcome contradicts timeout wait status")
    return values


def audit(directory):
    folder = Path(directory)
    lifecycle = folder / "host-gui-lifecycle.txt"
    if not lifecycle.is_file():
        raise ValueError("missing host X11/process lifecycle record")
    outcome = verify(lifecycle.read_bytes())
    host = folder / "input-probe.txt"
    guest = folder / "manual-result.txt"
    if not host.is_file() or not guest.is_file():
        raise ValueError("independent host-input or guest-control proof missing")
    log = host.read_text(encoding="ascii")
    if ("host_manual_probe_sent=yes" not in log.splitlines() and
        not any(line.startswith("host_manual_probe_sent=yes ") for line in log.splitlines())):
        raise ValueError("manual key injection not observed")
    if "host_plus_key_sent=yes" not in log.splitlines():
        raise ValueError("Plus key injection not observed")
    if not guest.read_text(encoding="ascii").startswith(
        "VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "
    ):
        raise ValueError("guest-side Plus/cleanup not independently verified")
    kind = outcome["host_process_outcome"]
    target = outcome["target_window_visible_after_plus"]
    # Even a clean host return does not establish that Plus caused it.
    result = ("VPD_NEXIUM_HOST_LIFECYCLE_CLASSIFIED "
              f"target_window_after_plus={target} "
              f"host_process_outcome={kind} "
              f"timeout_wrapper_wait_rc={outcome['timeout_wrapper_wait_rc']} "
              "guest_cleanup_verified=yes emulator_gui_exit_caused_by_plus_proven=no\n")
    (folder / "host-lifecycle-result.txt").write_text(result)
    print(result, end="")
    return outcome


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", required=True, type=Path)
    args = ap.parse_args()
    try:
        audit(args.evidence)
    except (OSError, ValueError, UnicodeError) as exc:
        args.evidence.mkdir(parents=True, exist_ok=True)
        (args.evidence / "host-lifecycle-result.txt").write_text(
            "INCONCLUSIVE: " + str(exc) + "\n")
        ap.exit(1, "NeXium host lifecycle unverified: " + str(exc) + "\n")
