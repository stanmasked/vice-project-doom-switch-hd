#!/usr/bin/env python3
"""Require actual NeXium kernel/runner evidence of a normal guest NRO exit.

The NeXium GUI can remain open after the emulated homebrew process exits.
This diagnostic deliberately does not assert host GUI termination or causality
from a keyboard event. It is independent of the app's SD witness.
"""
import argparse
from pathlib import Path
import re

MAX_LOG_BYTES = 1_000_000
EXPECTED_NRO = "vpd_native_scene.nro"
PREFIX = re.compile(
    r"^\[\d{2}:\d{2}:\d{2}\.\d{3}\] \[ INFO\] \[(?P<source>[^]]+)\] (?P<message>.*)$"
)
LOAD = re.compile(r"Loading NRO from: .*/vpd_native_scene\.nro")
EXIT = re.compile(
    r"svcExitProcess - terminating process \(x0=0x0 lr=0x[0-9a-fA-F]+\)"
)
COMPLETE = re.compile(r"Emulation complete: ([0-9]+) cycles, ([0-9]+) SVCs")
CORE = re.compile(r"\[core([123])\] stopped")
REQUIRED = ("load", "start", "exit_svc", "process_exited", "complete")
SOURCES = {
    "load": "nexium_kernel::boot",
    "start": "nexium_runner::boot",
    "exit_svc": "nexium_kernel::kernel::svc",
    "process_exited": "nexium_runner::boot",
    "complete": "nexium_runner::boot",
}


def verify_log(raw):
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_LOG_BYTES:
        raise ValueError("NeXium native log missing or oversized")
    if not raw.endswith(b"\n") or b"\r" in raw or b"\x00" in raw:
        raise ValueError("malformed NeXium kernel log line endings")
    lines = raw.decode("utf-8").splitlines()
    events = {}
    stopped = {}
    cycles = None
    svc_calls = None
    for idx, line in enumerate(lines):
        parsed = PREFIX.fullmatch(line)
        if not parsed:
            if any(t in line for t in (
                "Loading NRO from:", "Starting emulation loop", "svcExitProcess",
                "Process exited", "Emulation complete:", "] stopped"
            )):
                raise ValueError("malformed kernel/runner lifecycle event")
            continue
        source = parsed["source"]
        msg = parsed["message"]
        kind = None
        if "Loading NRO from:" in msg:
            if source != SOURCES["load"] or not LOAD.fullmatch(msg):
                raise ValueError("wrong NRO or untrusted loader log source")
            kind = "load"
        elif msg == "Starting emulation loop":
            kind = "start"
        elif msg.startswith("svcExitProcess"):
            if not EXIT.fullmatch(msg):
                raise ValueError("missing zero exit status from svcExitProcess")
            kind = "exit_svc"
        elif msg == "Process exited":
            kind = "process_exited"
        elif msg.startswith("Emulation complete:"):
            match = COMPLETE.fullmatch(msg)
            if not match:
                raise ValueError("malformed emulation-complete event")
            cycles, svc_calls = map(int, match.groups())
            if not 0 < cycles < 10**15 or not 0 < svc_calls < 10**8:
                raise ValueError("impossible emulator execution counts")
            kind = "complete"
        else:
            stopped_match = CORE.fullmatch(msg)
            if stopped_match:
                if source != "nexium_runner::boot":
                    raise ValueError("wrong source for stopped CPU core")
                core = stopped_match.group(1)
                if core in stopped:
                    raise ValueError("duplicate CPU core shutdown")
                stopped[core] = idx
            continue
        if source != SOURCES[kind] or kind in events:
            raise ValueError("duplicate or wrong-source kernel lifecycle event")
        events[kind] = idx
    if tuple(e for e in REQUIRED if e not in events):
        raise ValueError("missing native NeXium guest exit sequence")
    if list(events[k] for k in REQUIRED) != sorted(
        events[k] for k in REQUIRED
    ) or any(events[REQUIRED[i]] >= events[REQUIRED[i + 1]]
             for i in range(len(REQUIRED) - 1)):
        raise ValueError("kernel guest exit events are out of order")
    if set(stopped) != {"1", "2", "3"} or any(
        position <= events["complete"] for position in stopped.values()
    ):
        raise ValueError("guest CPU core stop records missing or too early")
    return {"cycles": cycles, "svc_calls": svc_calls,
            "core_stops": len(stopped), "guest_return_code": 0}


def audit(folder):
    root = Path(folder)
    log_dir = root / "xdg-config" / "NeXium" / "logs"
    files = sorted(log_dir.glob("nexium-*.log"))
    if len(files) != 1 or not files[0].is_file():
        raise ValueError("expected exactly one run-local NeXium native log")
    if not (root / "guest-manual-witness.txt").is_file():
        raise ValueError("guest manual input report absent")
    guest = root / "manual-result.txt"
    if not guest.is_file() or not guest.read_text(encoding="ascii").startswith(
        "VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "
    ):
        raise ValueError("independent manual input/cleanup audit has not passed")
    host = root / "host-lifecycle-result.txt"
    if not host.is_file() or not host.read_text(encoding="ascii").startswith(
        "VPD_NEXIUM_HOST_LIFECYCLE_CLASSIFIED "
    ):
        raise ValueError("independent GUI lifecycle audit has not passed")
    values = verify_log(files[0].read_bytes())
    result = (
        "VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "
        "kernel_svc_exit_process=yes guest_exit_code=0 "
        "runner_emulation_complete=yes guest_cpu_cores_stopped=3 "
        f"cycles={values['cycles']} svc_calls={values['svc_calls']} "
        "manual_guest_witness=yes gui_process_exit_proven=no "
        "exit_caused_by_plus_proven=no original_game_proven=no\n"
    )
    (root / "native-exit-result.txt").write_text(result)
    print(result, end="")
    return values


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError, ValueError, UnicodeError) as exc:
        args.evidence.mkdir(parents=True, exist_ok=True)
        (args.evidence / "native-exit-result.txt").write_text(
            "INCONCLUSIVE: " + str(exc) + "\n")
        parser.exit(1, "NeXium native process exit unverified: " + str(exc) + "\n")
