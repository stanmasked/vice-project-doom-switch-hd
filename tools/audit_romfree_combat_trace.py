#!/usr/bin/env python3
"""Independent full-trace audit of the self-authored ROM-free combat replay.

Runs host vpd_combat_replay --frames 200, never reads commercial ROM assets.
The full CSV SHA256 is pinned in addition to individual transition rules.
"""
import argparse
import csv
import hashlib
import io
import subprocess
from pathlib import Path

EXPECTED_SHA256 = "488674f6d2a7e506b1187fc4dcc4b28ab1f982fbf401966c661e4b63a0454f19"
FIELDS = ("frame", "buttons", "x_fixed", "y_fixed", "camera",
          "shots", "target_health", "target_hits", "active_projectiles",
          "fingerprint")
SAMPLES = {
    1: (8, 12288, 53760, 0, 1, 3, 0, 1, 12069486101437622842),
    58: (8, 12288, 53760, 0, 6, 2, 1, 5, 15449400794010182222),
    78: (8, 12288, 53760, 0, 8, 0, 3, 5, 3246776171472830100),
    200: (0, 12288, 53760, 0, 11, 0, 3, 0, 5947277116621119566),
}

class TraceError(ValueError):
    pass


def expected_buttons(frame):
    if frame <= 110:
        return 8
    if 116 <= frame <= 145:
        return 2
    if 146 <= frame <= 150:
        return 5
    if 151 <= frame <= 175:
        return 1
    return 0


def audit(data, *, sha256=EXPECTED_SHA256):
    if not isinstance(data, bytes) or len(data) > 65536 or not data.endswith(b"\n"):
        raise TraceError("CSV must be bounded and terminated by LF")
    if b"\r" in data or b"\x00" in data:
        raise TraceError("Unexpected binary/CRLF CSV data")
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise TraceError("Non-ASCII replay transcript") from exc
    parsed = list(csv.reader(io.StringIO(text), strict=True))
    if len(parsed) != 201 or tuple(parsed[0]) != FIELDS:
        raise TraceError("Missing header or exact 200-frame sequence")
    last_shots = last_hits = 0
    for frame, parts in enumerate(parsed[1:], 1):
        if len(parts) != len(FIELDS):
            raise TraceError("Incorrect number of CSV fields")
        try:
            values = tuple(int(item) for item in parts)
        except ValueError as exc:
            raise TraceError("Non-numeric frame data") from exc
        if any(str(number) != source for number, source in zip(values, parts)):
            raise TraceError("Noncanonical numeric frame data")
        frame_id, buttons, x, y, camera, shots, health, hits, active, hash64 = values
        if frame_id != frame or buttons != expected_buttons(frame):
            raise TraceError("Frame order or independent input schedule mismatch")
        if not (0 <= x < 64 * 16 * 256 and -256 * 32 <= y < 16 * 16 * 256
                and 0 <= camera <= 64 * 16 and
                last_shots <= shots <= 11 and shots-last_shots <= 1 and
                last_hits <= hits <= 3 and hits-last_hits <= 1 and
                health == 3-hits and hits <= shots and
                0 <= active <= 8 and
                0 <= hash64 <= 0xffffffffffffffff):
            raise TraceError("Impossible gameplay-state transition")
        if frame in SAMPLES and tuple(values[1:]) != SAMPLES[frame]:
            raise TraceError("Pinned intermediate or final frame mismatch")
        last_shots, last_hits = shots, hits
    digest = hashlib.sha256(data).hexdigest()
    if digest != sha256:
        raise TraceError("Full 200-frame CSV SHA-256 does not match independent reference")
    return {"frames": 200, "sha256": digest, "shots": last_shots,
            "hits": last_hits, "original_game_proven": False,
            "switch_runtime_proven": False}


def run(binary):
    executable = Path(binary)
    if not executable.is_file():
        raise TraceError("Compiled host replay executable is missing")
    completed = subprocess.run(
        [str(executable.resolve()), "--frames", "200"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=15, check=False)
    if completed.returncode != 0 or completed.stderr:
        raise TraceError("Host replay failed or emitted unexpected stderr")
    result = audit(completed.stdout)
    print("VPD_ROMFREE_FULL_COMBAT_TRACE_PASS "
          "frames=200 shots=11 target_hits=3 "
          f"sha256={result['sha256']} "
          "full_frame_state_audited=yes synthetic_only=yes "
          "original_game_proven=no switch_runtime_proven=no")
    return result


if __name__ == "__main__":
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--binary", type=Path, required=True)
    options = args.parse_args()
    try:
        run(options.binary)
    except (TraceError, subprocess.TimeoutExpired) as error:
        args.exit(1, f"Combat trace rejected: {error}\n")
