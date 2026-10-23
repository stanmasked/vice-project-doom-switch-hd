#!/usr/bin/env python3
"""Fail-closed audit of a full, pad-driven 3,197-frame ROM-free road route.

This proves the Switch prototype's automatic route gate and transition, not
the original NES clear predicate or authentic NES car physics.
"""
from __future__ import annotations

import argparse
from pathlib import Path

PREFIX = "VPD_DRIVING_ROUTE_V1"
KEYS = {
    "seq", "event", "frame", "car_x", "lateral_velocity", "speed",
    "health", "cooldown", "impacts", "obstacles_passed", "obstacle_serial",
    "obstacle_x", "obstacle_y", "left", "right", "throttle", "brake",
    "platform_fp", "source", "manual_exit", "route_complete",
    "original_stage_clear_proven",
}
LANES = (440, 570, 710, 840)


def parse_line(line: str) -> dict[str, str]:
    fields = line.split()
    if not fields or fields[0] != PREFIX:
        raise ValueError("wrong driving route witness marker")
    data: dict[str, str] = {}
    for token in fields[1:]:
        key, sep, value = token.partition("=")
        if not sep or not key or not value or key in data:
            raise ValueError("malformed or duplicate route witness field")
        data[key] = value
    if set(data) != KEYS:
        raise ValueError("route witness schema mismatch")
    return data


def verify_trace(text: str) -> dict[str, int]:
    lines = text.splitlines()
    if len(lines) < 180:
        raise ValueError("route trace too sparse for a full 3,197-frame run")
    baseline = None
    previous_frame = None
    previous_passed = 0
    previous_serial = 0
    previous_impacts = 0
    sample_count = 0
    saw_left = False
    saw_right = False
    final = None

    for index, line in enumerate(lines):
        data = parse_line(line)
        if int(data["seq"]) != index + 1:
            raise ValueError("route witness sequence gap or duplicate")
        numeric = {key: int(data[key]) for key in (
            "frame", "car_x", "lateral_velocity", "speed", "health",
            "cooldown", "impacts", "obstacles_passed", "obstacle_serial",
            "obstacle_x", "obstacle_y", "left", "right", "throttle", "brake",
            "manual_exit", "route_complete", "original_stage_clear_proven")}
        frame = numeric["frame"]
        fp = data["platform_fp"]
        if len(fp) != 16:
            raise ValueError("invalid platform fingerprint width")
        int(fp, 16)
        if baseline is None:
            baseline = fp
        if fp != baseline:
            raise ValueError("platform state changed during driving route")
        if numeric["original_stage_clear_proven"] != 0:
            raise ValueError("prototype route falsely claims original stage clear")
        if not 362 <= numeric["car_x"] <= 918:
            raise ValueError("car position outside prototype road bounds")
        if not -6 <= numeric["lateral_velocity"] <= 6:
            raise ValueError("lateral velocity outside prototype bounds")
        if not 0 <= numeric["speed"] <= 8:
            raise ValueError("speed outside prototype bounds")
        if not 1 <= numeric["health"] <= 5:
            raise ValueError("route did not keep the driver alive")
        if not 0 <= numeric["cooldown"] <= 45:
            raise ValueError("collision cooldown outside bounds")
        if not -110 <= numeric["obstacle_y"] <= 650:
            raise ValueError("obstacle position outside prototype bounds")
        if numeric["obstacle_x"] not in (440, 570, 640, 710, 840):
            raise ValueError("unknown obstacle lane")
        if any(numeric[k] not in (0, 1) for k in (
            "left", "right", "throttle", "brake", "manual_exit", "route_complete")):
            raise ValueError("invalid boolean route field")
        if numeric["left"] and numeric["right"]:
            raise ValueError("contradictory steering input")
        if numeric["throttle"] or numeric["brake"]:
            raise ValueError("route controller unexpectedly changed speed")
        if numeric["health"] != 5 - numeric["impacts"]:
            raise ValueError("health/impact counter mismatch")
        if numeric["obstacle_serial"] != (
            numeric["obstacles_passed"] + numeric["impacts"]):
            raise ValueError("obstacle pass/collision accounting mismatch")
        expected_lane = 640 if numeric["obstacle_serial"] == 0 else (
            LANES[numeric["obstacle_serial"] % 4])
        if numeric["obstacle_x"] != expected_lane:
            raise ValueError("obstacle lane does not match deterministic source state")
        if data["event"] == "sample":
            if index == len(lines) - 1:
                raise ValueError("route trace has no terminal exit record")
            if data["source"] != "libnx_pad":
                raise ValueError("route sample is not guest pad-loop evidence")
            if numeric["manual_exit"] != 0 or numeric["route_complete"] != 0:
                raise ValueError("sample forged an exit reason")
            if previous_frame is None:
                if frame != 16 or numeric["car_x"] != 640 or numeric["health"] != 5:
                    raise ValueError("route did not start from a fresh driving state")
                if numeric["obstacle_x"] != 640 or numeric["obstacle_y"] != 132:
                    raise ValueError("initial obstacle state mismatch")
            else:
                if frame <= previous_frame or frame - previous_frame > 16:
                    raise ValueError("route sampling gap or frame replay")
            if numeric["obstacles_passed"] < previous_passed:
                raise ValueError("passed-obstacle counter regressed")
            if numeric["obstacle_serial"] < previous_serial:
                raise ValueError("obstacle serial regressed")
            if numeric["impacts"] < previous_impacts:
                raise ValueError("impact counter regressed")
            saw_left = saw_left or bool(numeric["left"])
            saw_right = saw_right or bool(numeric["right"])
            sample_count += 1
            previous_frame = frame
            previous_passed = numeric["obstacles_passed"]
            previous_serial = numeric["obstacle_serial"]
            previous_impacts = numeric["impacts"]
        elif data["event"] == "exit_request":
            if index != len(lines) - 1:
                raise ValueError("records found after route exit request")
            if data["source"] != "libnx_frame":
                raise ValueError("route exit did not come from guest frame loop")
            if numeric["manual_exit"] != 0 or numeric["route_complete"] != 1:
                raise ValueError("route used the manual exit instead of progress gate")
            if frame != 3197:
                raise ValueError("automatic route exited at the wrong frame")
            if previous_frame is None or frame < previous_frame or frame - previous_frame > 16:
                raise ValueError("terminal route witness has a sampling gap")
            if numeric["obstacles_passed"] < 8:
                raise ValueError("route completed without required obstacle progress")
            if numeric["obstacles_passed"] < previous_passed:
                raise ValueError("terminal passed-obstacle counter regressed")
            if numeric["obstacle_serial"] < previous_serial:
                raise ValueError("terminal obstacle serial regressed")
            if numeric["impacts"] < previous_impacts:
                raise ValueError("terminal impact counter regressed")
            if not saw_left or not saw_right:
                raise ValueError("both directions of real pad steering were not observed")
            if sample_count < 180:
                raise ValueError("insufficient guest samples for full route")
            final = numeric
        else:
            raise ValueError("unknown route witness event")
    if final is None:
        raise ValueError("missing automatic route exit record")
    return {"frame": final["frame"], "passed": final["obstacles_passed"],
            "health": final["health"], "impacts": final["impacts"],
            "samples": sample_count}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    trace = (args.evidence / "guest-driving-route-witness.txt").read_text(
        encoding="ascii")
    result = verify_trace(trace)
    print("VPD_NEXIUM_DRIVING_ROUTE_PASS "
          f"frame={result['frame']} passed={result['passed']} "
          f"health={result['health']} impacts={result['impacts']} "
          f"samples={result['samples']} manual_exit=no "
          "original_stage_clear_proven=no")


if __name__ == "__main__":
    main()
