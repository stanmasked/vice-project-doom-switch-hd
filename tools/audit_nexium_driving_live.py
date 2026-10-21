#!/usr/bin/env python3
"""Fail-closed auditor for one real NeXium pad-controlled driving session.

An entirely fabricated trace may be used only by unit tests, never as
emulator-runtime evidence. CI validates the *guest SD* file and *X11* P6
captures made by the independent second emulator process.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

EVENTS = ("enter", "right_throttle", "left_brake", "impact", "exit")
KEYS = {
    "seq", "event", "before_frame", "frame", "before_x", "car_x",
    "before_speed", "speed", "before_health", "health", "impacts",
    "cooldown", "left", "right", "throttle", "brake",
    "platform_before", "platform_after", "source",
    "original_nes_physics_proven",
}
SCREENS = ("screen-drive-right", "screen-drive-left",
           "screen-drive-impact", "screen-drive-exit")


def verify_trace(text: str) -> None:
    lines = text.splitlines()
    if len(lines) != 5:
        raise ValueError("exactly five source-owned guest records required")
    prev_frame = -1
    baseline = None
    previous_health = 5
    for i, (line, event) in enumerate(zip(lines, EVENTS), 1):
        fields = line.split()
        if not fields or fields[0] != "VPD_DRIVING_GUEST_V1":
            raise ValueError("wrong guest witness marker")
        data = {}
        for piece in fields[1:]:
            key, delim, value = piece.partition("=")
            if not delim or key in data or not key or not value:
                raise ValueError("malformed or duplicate guest field")
            data[key] = value
        if set(data) != KEYS or data["event"] != event or int(data["seq"]) != i:
            raise ValueError("guest sequence/schema mismatch")
        if data["source"] != "libnx_pad" or data["original_nes_physics_proven"] != "0":
            raise ValueError("untrusted source or original-game claim")
        fp1, fp2 = data["platform_before"], data["platform_after"]
        if len(fp1) != 16 or len(fp2) != 16:
            raise ValueError("invalid full platform fingerprint")
        int(fp1, 16)
        int(fp2, 16)
        if fp1 != fp2 or (baseline is not None and fp1 != baseline):
            raise ValueError("platform simulation changed in driving mode")
        baseline = fp1
        values = {key: int(data[key]) for key in (
            "before_frame", "frame", "before_x", "car_x", "before_speed",
            "speed", "before_health", "health", "impacts", "cooldown",
            "left", "right", "throttle", "brake")}
        frame = values["frame"]
        if (frame < 0 or frame > 200000 or
            values["before_frame"] > frame or
            (i > 1 and frame <= prev_frame) or
            not 362 <= values["car_x"] <= 918 or
            not 0 <= values["speed"] <= 8 or
            values["health"] < 0 or values["health"] > 5):
            raise ValueError("frame, car or health out of bounds")
        if i == 1 and not (frame == 0 and values["health"] == 5 and
                           values["car_x"] == 640 and values["speed"] == 3):
            raise ValueError("not a fresh driving entry")
        if i == 2 and not (
            values["right"] == values["throttle"] == 1 and
            values["left"] == values["brake"] == 0 and
            values["car_x"] > values["before_x"] and
            values["speed"] > values["before_speed"]):
            raise ValueError("no right+throttle physical response")
        if i == 3 and not (
            values["left"] == values["brake"] == 1 and
            values["right"] == values["throttle"] == 0 and
            values["car_x"] < values["before_x"] and
            values["speed"] < values["before_speed"]):
            raise ValueError("no left+brake physical response")
        if i == 4 and not (
            values["before_health"] == 5 and values["health"] == 4 and
            values["impacts"] == 1 and values["cooldown"] == 45):
            raise ValueError("no genuine single source collision")
        if i == 5 and not (
            values["health"] == previous_health == 4 and
            values["impacts"] == 1 and
            values["before_frame"] == frame):
            raise ValueError("not a valid driving-mode exit")
        if i in (1, 2, 3) and values["health"] != 5:
            raise ValueError("premature unexplained driving damage")
        prev_frame = frame
        previous_health = values["health"]


def p6_payload(path: Path) -> bytes:
    raw = path.read_bytes()
    if not raw.startswith(b"P6"):
        raise ValueError("not a P6 X11 screenshot: " + path.name)
    i = 2
    tokens = []
    while len(tokens) < 3:
        while i < len(raw) and raw[i] in b" \t\r\n":
            i += 1
        if i < len(raw) and raw[i] == 35:
            i = raw.find(b"\n", i)
            if i < 0:
                raise ValueError("truncated screenshot comment")
            continue
        start = i
        while i < len(raw) and raw[i] not in b" \t\r\n":
            i += 1
        if i == start or i >= len(raw):
            raise ValueError("incomplete P6 header")
        tokens.append(int(raw[start:i]))
    if raw[i] not in b" \t\r\n":
        raise ValueError("P6 header delimiter missing")
    width, height, maxval = tokens
    payload = raw[i + 1:]
    if (width, height, maxval) != (1280, 720, 255) or len(payload) != width * height * 3:
        raise ValueError("wrong X11 framebuffer dimensions or length")
    return payload


def verify_evidence(folder: Path) -> None:
    trace = (folder / "guest-driving-witness.txt").read_text(encoding="ascii")
    verify_trace(trace)
    hashes = [hashlib.sha256(p6_payload(folder / (name + ".ppm"))).hexdigest()
              for name in SCREENS]
    if len(set(hashes)) != len(hashes):
        raise ValueError("duplicated X11 frame: static or replayed screen")
    print("VPD_NEXIUM_DRIVING_LIVE_PASS guest_events=5 "
          "pad_state_changes=2 collision_hp=5_to_4 "
          "platform_frozen=yes distinct_x11_frames=4 "
          "original_nes_physics_proven=no")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    verify_evidence(args.evidence)


if __name__ == "__main__":
    main()
