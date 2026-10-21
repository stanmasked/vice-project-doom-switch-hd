#!/usr/bin/env python3
"""Independent same-frame driving framebuffer auditor. ROM-free only."""
from __future__ import annotations
import argparse
from pathlib import Path

EVENTS = {"2": "right_throttle", "4": "impact"}
EXPECTED_KEYS = {
    "seq", "frame", "car_x", "health", "flash",
    "car_pixel", "hud_pixel", "car_expected", "hud_expected",
    "source", "same_frame", "original_assets_used",
}
def parse_line(line: str, prefix: str) -> dict[str, str]:
    tokens = line.split()
    if not tokens or tokens[0] != prefix:
        raise ValueError("missing native witness prefix")
    fields = {}
    for token in tokens[1:]:
        k, sep, v = token.partition("=")
        if not sep or not k or not v or k in fields:
            raise ValueError("malformed raster witness")
        fields[k] = v
    return fields

def audit(folder: Path) -> None:
    control = (folder / "guest-driving-witness.txt").read_text("ascii").splitlines()
    pixels = (folder / "guest-driving-raster-witness.txt").read_text("ascii").splitlines()
    if len(control) != 5 or len(pixels) != 2:
        raise ValueError("need five control and two raster records")
    source = {}
    for line in control:
        fields = parse_line(line, "VPD_DRIVING_GUEST_V1")
        if fields.get("seq") in EVENTS:
            if fields.get("event") != EVENTS[fields["seq"]]:
                raise ValueError("wrong vehicle source event")
            source[fields["seq"]] = fields
    if set(source) != set(EVENTS):
        raise ValueError("driving control witness incomplete")
    for expected_seq, line in zip(("2", "4"), pixels):
        fields = parse_line(line, "VPD_DRIVING_RASTER_V1")
        if set(fields) != EXPECTED_KEYS or fields["seq"] != expected_seq:
            raise ValueError("raster witness schema or order mismatch")
        if (fields["source"] != "libnx_drawScene" or
            fields["same_frame"] != "yes" or fields["original_assets_used"] != "0"):
            raise ValueError("not actual source renderer")
        target = source[expected_seq]
        for key in ("frame", "car_x", "health"):
            if fields[key] != target[key]:
                raise ValueError("raster event does not share physics frame: " + key)
        frame = int(fields["frame"])
        health = int(fields["health"])
        flash = int(fields["flash"])
        if frame < 1 or not 0 <= health <= 5 or flash not in (0, 1):
            raise ValueError("invalid driving status")
        cooldown = int(target["cooldown"])
        if flash != int(cooldown > 0 and (frame // 4) % 2 == 0):
            raise ValueError("collision flash phase does not match same frame")
        car_color = 0xff7ec8e8 if flash else 0xff3f2fa3
        hud_color = 0xff5b55d3 if health == 5 else 0xff271911
        def color(field: str) -> int:
            raw = fields[field]
            if len(raw) != 8 or any(c not in "0123456789abcdef" for c in raw):
                raise ValueError("invalid native RGBA pixel")
            return int(raw, 16)
        if (color("car_pixel") != car_color or
            color("car_expected") != car_color or
            color("hud_pixel") != hud_color or
            color("hud_expected") != hud_color):
            raise ValueError("car or fifth HUD health pixel does not match source")
    print("VPD_NEXIUM_DRIVING_RASTER_PASS"
          " exact_guest_frames=2 source_car_pixel=yes"
          " source_fifth_heart=5_to_4 source_impact_flash=yes"
          " original_assets_used=no")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    audit(parser.parse_args().evidence)
if __name__ == "__main__":
    main()
