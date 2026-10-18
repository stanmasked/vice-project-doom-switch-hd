#!/usr/bin/env python3
"""Audit guest-written NeXium dash effects, never host-sent keys alone."""
import argparse
from pathlib import Path
import re

MARKER = "VPD_ROMFREE_DASH_V1"
EVENTS = ("start", "complete")
FIELDS = ("seq", "event", "frame", "delta_fixed", "cooldown",
          "source", "mode", "original_game_proven")
MAX_BYTES = 640


def verify(raw):
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BYTES:
        raise ValueError("dash guest record missing or oversized")
    text = raw.decode("ascii")
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise ValueError("malformed guest dash record line endings")
    lines = text.splitlines()
    if len(lines) != 2:
        raise ValueError("need exactly two native guest dash events")
    frames = []
    for idx, (event, line) in enumerate(zip(EVENTS, lines), 1):
        words = line.split(" ")
        if len(words) != len(FIELDS) + 1 or words[0] != MARKER:
            raise ValueError("invalid guest dash record format")
        pairs = [word.split("=", 1) for word in words[1:]]
        if any(len(pair) != 2 for pair in pairs):
            raise ValueError("invalid dash field separator")
        if tuple(key for key, value in pairs) != FIELDS:
            raise ValueError("incorrect guest dash schema order")
        record = dict(pairs)
        if record["seq"] != str(idx) or record["event"] != event:
            raise ValueError("dash events are missing, reordered or duplicated")
        if record["source"] != "ZR+Right" or record["mode"] != "manual" or (
            record["original_game_proven"] != "no"
        ):
            raise ValueError("wrong guest input source or attestation scope")
        for key in ("frame", "delta_fixed", "cooldown"):
            value = record[key]
            if not re.fullmatch(r"0|[1-9][0-9]*", value):
                raise ValueError("noncanonical dash numerical field")
        frame = int(record["frame"])
        if not 1 <= frame <= 1200:
            raise ValueError("dash frame outside bounded emulation period")
        if int(record["delta_fixed"]) != (1536 if idx == 1 else 9216):
            raise ValueError("dash displacement does not match observed physics")
        if int(record["cooldown"]) != (45 if idx == 1 else 40):
            raise ValueError("dash cooldown inconsistent with six-tick burst")
        frames.append(frame)
    if frames[1] != frames[0] + 5:
        raise ValueError("dash completion must follow exactly five more ticks")
    return {"start_frame": frames[0], "complete_frame": frames[1]}


def audit(folder):
    base = Path(folder)
    path = base / "guest-dash-witness.txt"
    if not path.is_file():
        raise ValueError("no NeXium guest-created dash witness")
    result = verify(path.read_bytes())
    host = base / "input-probe.txt"
    if not host.is_file() or (
        "host_dash_probe_sent=yes keys=D+T expected=ZR+Right"
        not in host.read_text(encoding="ascii").splitlines()
    ):
        raise ValueError("host ZR+Right probe was not submitted")
    for name, prefix in (
        ("manual-result.txt", "VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "),
        ("native-exit-result.txt", "VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
    ):
        marker = base / name
        if not marker.is_file() or not marker.read_text(
            encoding="ascii"
        ).startswith(prefix):
            raise ValueError("required independent guest/exit proof missing: " + name)
    output = (
        "VPD_NEXIUM_GUEST_DASH_PASS guest_input=ZR+Right "
        "guest_start=yes guest_six_tick_burst=yes "
        f"start_frame={result['start_frame']} "
        f"complete_frame={result['complete_frame']} "
        "delta_fixed=9216 cooldown_at_start=45 cooldown_at_end=40 "
        "guest_sd_witness=yes original_game_proven=no\n"
    )
    (base / "dash-result.txt").write_text(output, encoding="ascii")
    print(output, end="")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError, UnicodeError, ValueError) as exc:
        args.evidence.mkdir(parents=True, exist_ok=True)
        (args.evidence / "dash-result.txt").write_text(
            "INCONCLUSIVE: " + str(exc) + "\n", encoding="ascii")
        parser.exit(1, "NeXium guest ZR dash unverified: " + str(exc) + "\n")
