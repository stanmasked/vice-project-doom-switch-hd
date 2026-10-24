#!/usr/bin/env python3
"""Fail-closed auditor for 41 actual libnx guest framebuffer records.

The numeric source-frame labels are published aggregate references only.
This audit never claims an original NES capture, source art or physics.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

MARKER = "VPD_STAGE365_NUMERIC_DEMO_V2"
EXPECTED_EDGE = "ffefda66"
EXPECTED_PANEL = "ff5b4118"
REQUIRED = {
    "source": "libnx_drawScene",
    "actual_original_rom_source_verification": "0",
    "original_game_physics_proven": "0",
    "raw_rom_fm2_present": "0",
}


def parse_line(line: str) -> dict:
    parts = line.strip().split()
    if not parts or parts[0] != MARKER:
        raise ValueError("not a Stage365 actual libnx guest record")
    parsed = {}
    for part in parts[1:]:
        if part.count("=") != 1:
            raise ValueError("malformed guest field")
        key, value = part.split("=")
        if not key or not value or key in parsed:
            raise ValueError("empty or duplicate guest field")
        parsed[key] = value
    required = {
        "event", "original_pair_start", "guest_frame", "image_shift",
        "panel_pixel", "edge_pixel", "demo_glyph_pixel", "platform_fp",
        *REQUIRED,
    }
    if set(parsed) != required:
        raise ValueError("wrong Stage365 guest schema")
    for key, value in REQUIRED.items():
        if parsed[key] != value:
            raise ValueError("guest evidence claims unverified original source/physics")
    for key, value in (
        ("panel_pixel", EXPECTED_PANEL),
        ("edge_pixel", EXPECTED_EDGE),
        ("demo_glyph_pixel", EXPECTED_EDGE),
    ):
        if parsed[key].lower() != value:
            raise ValueError("actual libnx framebuffer sample mismatch")
    for key in ("original_pair_start", "guest_frame", "image_shift"):
        if not parsed[key].isdigit():
            raise ValueError("invalid guest numeric value")
    fp = parsed["platform_fp"]
    if len(fp) != 16 or any(c not in "0123456789abcdefABCDEF" for c in fp):
        raise ValueError("invalid platform fingerprint")
    return parsed


def audit_sequence(host: str, driving: str, guest: str) -> dict:
    required_host = (
        "physical_keyboard_chord=R+T+Q Switch=ZL+ZR+L",
        "native_driving_enter=yes",
        "guest_v2_records=41",
        "guest_v2_first=on",
        "guest_v2_last=last",
        "STAGE365_REAL_NEXIUM_FULL_SEQUENCE_OBSERVED",
    )
    if any(marker not in host for marker in required_host):
        raise ValueError("missing actual NeXium controller/sequence host witness")
    if "VPD_DRIVING_GUEST_V1 seq=1 event=enter " not in driving:
        raise ValueError("missing actual native manual driving guest entry")
    rows = guest.splitlines()
    if len(rows) != 41:
        raise ValueError("must contain all 41 and only 41 guest presentation states")
    parsed = [parse_line(row) for row in rows]
    fingerprints = set()
    first_guest = None
    for i, row in enumerate(parsed):
        pair = 519 + i
        event = "on" if i == 0 else "last" if i == 40 else "frame"
        shift = 3 if pair <= 526 else 4 if pair <= 558 else 5
        if (row["original_pair_start"] != str(pair) or
            row["event"] != event or row["image_shift"] != str(shift)):
            raise ValueError("missing, duplicated, reordered or incorrect numeric state")
        frame = int(row["guest_frame"])
        if first_guest is None:
            first_guest = frame
            if frame < 1:
                raise ValueError("invalid first presented guest frame")
        elif frame != first_guest + i:
            raise ValueError("guest presentation frames are not contiguous")
        fingerprints.add(row["platform_fp"])
    if len(fingerprints) != 1:
        raise ValueError("platform simulation fingerprint changed during source-safe overlay")
    if int(parsed[-1]["guest_frame"]) - int(parsed[0]["guest_frame"]) != 40:
        raise ValueError("guest frame interval does not span all 41 presentations")
    return {
        "format": "vpd_stage365_real_nexium_full_guest_sequence_v1",
        "actual_native_guest_records": 41,
        "first_numeric_reference_pair": 519,
        "last_numeric_reference_pair": 559,
        "presentation_frames_contiguous": True,
        "guest_frame_delta": 40,
        "shift_sequence": {"519-526": 3, "527-558": 4, "559": 5},
        "every_guest_frame_panel_edge_and_glyph_pixel_checked": True,
        "one_unchanged_source_free_platform_fingerprint_all_41_frames": True,
        "manual_input_chord": "NeXium R+T+Q => Switch ZL+ZR+L",
        "original_nes_rom_or_fm2_used": False,
        "original_game_camera_or_vehicle_physics_proven": False,
    }


def audit_screenshots(path: Path, result: dict) -> dict:
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Pillow required for independent real X11 screenshot audit") from exc
    matches = []
    for p in sorted(path.glob("screen-demo-*.png")):
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 8_000_000:
            raise ValueError("invalid or oversized host screenshot")
        with Image.open(p) as im:
            if im.size != (1280, 720):
                continue
            rgb = im.convert("RGB")
            px = rgb.load()
            sampled = 0
            exact = 0
            for y in range(250, 380, 3):
                for x in range(850, 1280, 3):
                    r, g, b = px[x, y]
                    if 95 <= r <= 110 and 210 <= g <= 228 and 231 <= b <= 246:
                        sampled += 1
                    if (r, g, b) == (102, 218, 239):
                        exact += 1
            if sampled >= 5:
                matches.append({"file": p.name, "sampled_cyan_pixels": sampled,
                                "exact_cyan_samples": exact})
    if not matches:
        raise ValueError("no real X11 screenshot captured the guest DEMO overlay")
    result["real_host_screenshot_check"] = "present"
    result["real_host_screenshot_files_with_DEMO"] = matches
    return result


def audit_dir(path: Path) -> dict:
    def read(name: str) -> str:
        p = path / name
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 1_000_000:
            raise ValueError("missing, symlinked or oversized evidence: " + name)
        return p.read_text(encoding="utf-8")
    result = audit_sequence(read("host-events.txt"), read("guest-driving-enter.txt"),
                            read("guest-scroll-demo-v2.txt"))
    return audit_screenshots(path, result)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence", required=True, type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    try:
        msg = json.dumps(audit_dir(args.evidence), sort_keys=True, indent=2) + "\n"
        if args.output:
            if args.output.exists() or args.output.is_symlink():
                raise ValueError("will not overwrite prior verdict")
            args.output.write_text(msg, encoding="utf-8")
        else:
            print(msg, end="")
    except (OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
        ap.exit(1, "STAGE365_FULL_GUEST_SEQUENCE_UNCONFIRMED: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
