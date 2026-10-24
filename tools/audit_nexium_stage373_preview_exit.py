#!/usr/bin/env python3
"""Fail-closed real NeXium preview-exit reset/restart/terminal-off audit for the source-safe numeric DEMO."""
from __future__ import annotations
import argparse
import json
import re
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
        "physical_keyboard_chord_exit_preview=R+T+V Switch=ZL+ZR+X",
        "physical_keyboard_chord_restart=R+T+Q Switch=ZL+ZR+L",
        "preview_exit_screenshot_captured=yes",
        "screen_preview_exited_cyan_pixels=0",
        "guest_trace_stable_while_preview_off=yes",
        "guest_trace_stable_after_complete=yes",
        "screen_completed_cyan_pixels=0",
        "STAGE373_REAL_NEXIUM_PREVIEW_EXIT_RESET_OBSERVED",
        "STAGE373_REAL_NEXIUM_TERMINAL_OFF_OBSERVED",
    )
    if any(marker not in host for marker in required_host):
        raise ValueError("missing real host input, preview-exit or off-screen witness")
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
        host_int("guest_trace_after_preview_exit_count") != len(first) or
        host_int("second_session_records") != len(second) or
        host_int("total_guest_records") != len(parsed) or
        host_int("guest_trace_after_complete_count") != len(parsed)):
        raise ValueError("host counts do not match the actual guest trace or post-completion count")
    validate_session(first, complete=False)
    validate_session(second, complete=True)
    # Preview exit resets driving_state, so the second session starts a fresh
    # guest-frame timeline. Enforce contiguity within each session, not across
    # the explicit preview reset boundary.
    if (len({r["platform_fp"] for r in first}) != 1 or
        len({r["platform_fp"] for r in second}) != 1):
        raise ValueError("source-free platform fingerprint changed within a session")
    return {
        "format": "vpd_stage373_real_nexium_preview_exit_reset_terminal_off_v1",
        "actual_native_guest_sessions": 2,
        "first_session_states_before_cancel": len(first),
        "first_session_stopped_by_preview_exit_before_final_pair": True,
        "second_session_states_after_fresh_edge": len(second),
        "second_session_restarted_at_numeric_pair": 519,
        "second_session_reached_final_numeric_pair": 559,
        "first_session_guest_frames_contiguous": True,
        "restarted_session_guest_frames_contiguous": True,
        "guest_trace_stopped_while_preview_was_exited": True,
        "post_completion_guest_trace_stable": True,
        "preview_exit_screenshot_has_no_cyan_demo_panel_samples": True,
        "terminal_preview_exit_screenshot_has_no_cyan_demo_panel_samples": True,
        "platform_fingerprint_stable_within_each_session": True,
        "original_nes_rom_or_fm2_used": False,
        "original_game_camera_or_vehicle_physics_proven": False,
    }


def screenshot_pixel_counts(path: Path) -> dict:
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Pillow is required for independent screenshot audit") from exc
    result = {}
    for name in ("screen-demo-start.png", "screen-preview-exited.png", "screen-restart.png", "screen-completed.png"):
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
    if result["screen-preview-exited.png"] != 0:
        raise ValueError("preview-exit screenshot still contains DEMO cyan panel pixels")
    if result["screen-restart.png"] < 20:
        raise ValueError("restart screenshot did not show the DEMO panel again")
    if result["screen-completed.png"] != 0:
        raise ValueError("terminal screenshot still contains DEMO cyan panel pixels")
    return result



def audit_provenance(host: str, nro_sha_text: str, attestation: str,
                     release_verification: str) -> dict:
    """Bind runtime evidence to the exact guest NRO and verified NeXium asset."""
    nro_lines = nro_sha_text.splitlines()
    if len(nro_lines) != 1:
        raise ValueError("guest NRO digest file must contain exactly one sha256sum record")
    nro_parts = nro_lines[0].split()
    if (len(nro_parts) != 2 or
        not re.fullmatch(r"[0-9a-f]{64}", nro_parts[0]) or
        Path(nro_parts[1]).name != "vpd_native_scene.nro"):
        raise ValueError("invalid exact guest NRO SHA-256 record")
    nro_digest = nro_parts[0]
    host_digests = [line.split("=", 1)[1] for line in host.splitlines()
                    if line.startswith("nro_sha256=")]
    if len(host_digests) != 1 or host_digests[0] != nro_digest:
        raise ValueError("host capture does not bind to the exact guest NRO digest")

    values = {}
    for line in attestation.splitlines():
        if line.count("=") != 1:
            raise ValueError("malformed NeXium release attestation")
        key, value = line.split("=", 1)
        if not key or not value or key in values:
            raise ValueError("empty or duplicate NeXium release attestation field")
        values[key] = value
    required = {
        "nexium_release_id", "nexium_asset_id", "nexium_tag",
        "nexium_published_at", "nexium_archive_sha256",
        "nexium_asset_size_bytes", "nexium_digest_source", "nexium_mutable_tag",
    }
    if set(values) != required:
        raise ValueError("wrong NeXium release attestation schema")
    if (not values["nexium_release_id"].isdigit() or
        not values["nexium_asset_id"].isdigit() or
        not values["nexium_asset_size_bytes"].isdigit()):
        raise ValueError("invalid NeXium release/asset numeric metadata")
    archive_digest = values["nexium_archive_sha256"]
    if not re.fullmatch(r"[0-9a-f]{64}", archive_digest):
        raise ValueError("invalid NeXium archive SHA-256 in attestation")
    size = int(values["nexium_asset_size_bytes"])
    if not 40_000_000 <= size <= 350_000_000:
        raise ValueError("implausible attested NeXium archive size")
    if (values["nexium_tag"] != "nightly" or
        values["nexium_digest_source"] != "github_release_api" or
        values["nexium_mutable_tag"] != "yes"):
        raise ValueError("NeXium release provenance is not the expected official mutable nightly")
    verification_lines = release_verification.strip().splitlines()
    if len(verification_lines) != 1:
        raise ValueError("missing or ambiguous NeXium release verification result")
    match = re.fullmatch(
        r"VERIFIED: official GitHub NeXium release asset SHA-256 ([0-9a-f]{64}) asset_id ([0-9]+)",
        verification_lines[0],
    )
    if not match:
        raise ValueError("NeXium release verification did not report a successful official digest check")
    if (match.group(1) != archive_digest or
        match.group(2) != values["nexium_asset_id"]):
        raise ValueError("NeXium release verification output disagrees with its attestation")
    return {
        "guest_nro_sha256": nro_digest,
        "guest_nro_digest_matches_host_capture": True,
        "nexium_release_attestation_verified": True,
        "nexium_release_asset_sha256": archive_digest,
        "nexium_release_id": int(values["nexium_release_id"]),
        "nexium_asset_id": int(values["nexium_asset_id"]),
        "nexium_release_tag": values["nexium_tag"],
        "nexium_release_tag_is_mutable": True,
    }


def audit_dir(path: Path) -> dict:
    def read(name: str) -> str:
        p = path / name
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 1_000_000:
            raise ValueError("missing, symlinked or oversized evidence: " + name)
        return p.read_text(encoding="utf-8")
    host = read("host-events.txt")
    result = audit_sequence(host, read("manual-witness.txt"),
                            read("guest-driving-enter.txt"), read("guest-scroll-demo-v2.txt"))
    result.update(audit_provenance(
        host, read("guest-nro-sha256.txt"),
        read("neXium-release-attestation.txt"), read("release-verification.txt")))
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
        ap.exit(1, "STAGE373_NEXIUM_PREVIEW_EXIT_UNCONFIRMED: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
