#!/usr/bin/env python3
"""Fail-closed real NeXium cancel/restart/terminal-off audit for the source-safe numeric DEMO."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from audit_nexium_stage365_sequence import parse_line

MARKER = "VPD_STAGE365_NUMERIC_DEMO_V2"


def validate_session(rows: list[dict], *, complete: bool) -> None:
    if complete and len(rows) != 41:
        raise ValueError("restarted session must contain all 41 states")
    if not complete and not 6 <= len(rows) <= 16:
        raise ValueError("first session must be visibly interrupted after 6–16 states")
    for i, row in enumerate(rows):
        pair = 519 + i
        expected_event = "on" if i == 0 else (
            "last" if complete and i == 40 else "frame")
        shift = 3 if pair <= 526 else 4 if pair <= 558 else 5
        if (row["original_pair_start"] != str(pair) or
            row["event"] != expected_event or
            row["image_shift"] != str(shift)):
            raise ValueError("session contains a skipped, repeated or wrong pair/event")
    frames = [int(row["guest_frame"]) for row in rows]
    if any(b != a + 1 for a, b in zip(frames, frames[1:])):
        raise ValueError("guest presentation frames are not contiguous within session")


def audit_sequence(host: str, manual: str, driving: str, guest: str) -> dict:
    required_host = (
        "guest_sd_witness_files_ready=yes",
        "native_manual_entry=yes",
        "native_driving_enter=yes",
        "physical_keyboard_chord_start=R+T+Q Switch=ZL+ZR+L",
        "physical_keyboard_chord_cancel=R+T+Q Switch=ZL+ZR+L",
        "physical_keyboard_chord_restart=R+T+Q Switch=ZL+ZR+L",
        "cancel_screenshot_captured=yes",
        "guest_trace_stable_while_off=yes",
        "guest_trace_stable_after_complete=yes",
        "screen_completed_cyan_pixels=0",
        "STAGE371_REAL_NEXIUM_CANCEL_RESTART_OBSERVED",
        "STAGE372_REAL_NEXIUM_TERMINAL_OFF_OBSERVED",
    )
    if any(marker not in host for marker in required_host):
        raise ValueError("missing real host input, cancellation or off-screen witness")
    if ("VPD_ROMFREE_MANUAL_V1 seq=1 event=enter frame=0 metric=1 "
        "mode=manual original_game_proven=no" not in manual):
        raise ValueError("missing actual NRO-owned manual entry witness")
    if "VPD_DRIVING_GUEST_V1 seq=1 event=enter " not in driving:
        raise ValueError("missing actual NRO-owned driving-preview entry")
    rows = guest.splitlines()
    if not rows:
        raise ValueError("no actual guest trace")
    parsed = [parse_line(row) for row in rows]
    starts = [i for i, row in enumerate(parsed) if row["event"] == "on"]
    lasts = [i for i, row in enumerate(parsed) if row["event"] == "last"]
    if len(starts) != 2 or starts[0] != 0:
        raise ValueError("trace must contain exactly two real DEMO starts")
    if len(lasts) != 1 or lasts[0] != len(parsed) - 1:
        raise ValueError("only the restarted session may reach the final state")
    first = parsed[:starts[1]]
    second = parsed[starts[1]:]
    def host_int(key: str) -> int:
        prefix = key + "="
        matches = [line[len(prefix):] for line in host.splitlines()
                   if line.startswith(prefix)]
        if len(matches) != 1 or not matches[0].isdigit():
            raise ValueError("missing or invalid host count: " + key)
        return int(matches[0])
    if (host_int("first_session_records") != len(first) or
        host_int("guest_trace_after_off_count") != len(first) or
        host_int("second_session_records") != len(second) or
        host_int("total_guest_records") != len(parsed) or
        host_int("guest_trace_after_complete_count") != len(parsed)):
        raise ValueError("host counts do not match the actual guest trace or post-completion count")
    validate_session(first, complete=False)
    validate_session(second, complete=True)
    if int(second[0]["guest_frame"]) <= int(first[-1]["guest_frame"]):
        raise ValueError("restart did not occur at a later guest frame")
    if len({r["platform_fp"] for r in parsed}) != 1:
        raise ValueError("source-free platform fingerprint changed during cancel/restart")
    return {
        "format": "vpd_stage372_real_nexium_cancel_restart_terminal_off_v1",
        "actual_native_guest_sessions": 2,
        "first_session_states_before_cancel": len(first),
        "first_session_cancelled_before_final_pair": True,
        "second_session_states_after_fresh_edge": len(second),
        "second_session_restarted_at_numeric_pair": 519,
        "second_session_reached_final_numeric_pair": 559,
        "first_session_guest_frames_contiguous": True,
        "restarted_session_guest_frames_contiguous": True,
        "guest_trace_stopped_while_demo_overlay_was_off": True,
        "post_completion_guest_trace_stable": True,
        "off_screenshot_has_no_cyan_demo_panel_samples": True,
        "terminal_off_screenshot_has_no_cyan_demo_panel_samples": True,
        "same_source_free_platform_fingerprint_across_both_sessions": True,
        "original_nes_rom_or_fm2_used": False,
        "original_game_camera_or_vehicle_physics_proven": False,
    }


def screenshot_pixel_counts(path: Path) -> dict:
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Pillow is required for independent screenshot audit") from exc
    result = {}
    for name in ("screen-demo-start.png", "screen-cancelled.png", "screen-restart.png", "screen-completed.png"):
        p = path / name
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 8_000_000:
            raise ValueError("missing, symlinked or oversized screenshot: " + name)
        with Image.open(p) as im:
            if im.size != (1280, 720):
                raise ValueError("unexpected X11 screenshot dimensions: " + name)
            rgb = im.convert("RGB")
            px = rgb.load()
            count = 0
            # Only the fixed right-side overlay rectangle, not the road or HUD.
            for y in range(245, 336):
                for x in range(1010, 1205):
                    if px[x, y] == (102, 218, 239):
                        count += 1
        result[name] = count
    if result["screen-demo-start.png"] < 20:
        raise ValueError("first real screenshot did not show the DEMO panel")
    if result["screen-cancelled.png"] != 0:
        raise ValueError("cancel screenshot still contains DEMO cyan panel pixels")
    if result["screen-restart.png"] < 20:
        raise ValueError("restart screenshot did not show the DEMO panel again")
    if result["screen-completed.png"] != 0:
        raise ValueError("terminal screenshot still contains DEMO cyan panel pixels")
    return result


def audit_dir(path: Path) -> dict:
    def read(name: str) -> str:
        p = path / name
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 1_000_000:
            raise ValueError("missing, symlinked or oversized evidence: " + name)
        return p.read_text(encoding="utf-8")
    result = audit_sequence(read("host-events.txt"), read("manual-witness.txt"),
                            read("guest-driving-enter.txt"), read("guest-scroll-demo-v2.txt"))
    result["real_x11_exact_cyan_pixel_counts"] = screenshot_pixel_counts(path)
    return result


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
        ap.exit(1, "STAGE372_NEXIUM_TERMINAL_OFF_UNCONFIRMED: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
