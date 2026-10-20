#!/usr/bin/env python3
"""Prove real LOW HP pulse ON -> OFF -> terminal death -> clean replay on X11.

No new game inputs, clocks, graphics or simulation: re-audit four screenshots
from the SAME successful second-run, guest-attested NeXium execution.
"""
import argparse
import re
from pathlib import Path

from audit_nexium_defeat_retry import verify as verify_defeat
from audit_nexium_fourth_stage import raster
from audit_nexium_hd_fx_sentry_hit import LIVE_HEART_RECTS, FIFTH_HEART_RECT
from audit_nexium_hd_low_health import (
    source_witness, verify_phase, hp2_warning, count_color, TEAL, FLASH, EMPTY,
)

RECORD = re.compile(
    r"VPD_NEXIUM_HD_LOW_HEALTH_PASS .*?live_x11_sample=([0-2]) "
    r"underline_pixels=([0-9]+) label_pixels=([0-9]+) "
    r"ppm_sha256=([a-f0-9]{64}) "
)
RECTS = (*LIVE_HEART_RECTS, FIFTH_HEART_RECT)


def source_hearts(frame, health):
    """Never mistake synthetic label pixels for native source heart state."""
    if health not in (0, 2, 5):
        raise ValueError("invalid source HP phase to verify")
    for n, (left, right) in enumerate(RECTS):
        rect = (left, 17, right + 1, 29)
        filled = count_color(frame, rect, TEAL) + count_color(frame, rect, FLASH)
        empty = count_color(frame, rect, EMPTY)
        if n < health:
            if filled < 110 or empty:
                raise ValueError(f"source heart {n+1} not correctly filled at HP{health}")
        elif empty < 110 or filled:
            raise ValueError(f"source heart {n+1} not correctly empty at HP{health}")


def verify_lifecycle(on, off, dead, retry):
    """Accept only true four-state native pixel evidence."""
    source_hearts(on, 2)
    source_hearts(off, 2)
    source_hearts(dead, 0)
    source_hearts(retry, 5)

    active, line, glyph = hp2_warning(on)
    if not active or line < 180 or glyph < 40:
        raise ValueError("live source HP2 does not show both warning elements")
    for tag, raster_pixels in (("quiet HP2", off), ("death HP0", dead),
                               ("restart HP5", retry)):
        _, quiet_line, quiet_label = hp2_warning(raster_pixels)
        if quiet_line or quiet_label:
            raise ValueError(f"LOW HP warning leaked into {tag}")
    return {"warning_line": line, "warning_label": glyph}


def audit(folder):
    root = Path(folder)
    base_pass = (root / "hd-low-health-result.txt").read_text("ascii")
    match = RECORD.search(base_pass)
    if not base_pass.startswith("VPD_NEXIUM_HD_LOW_HEALTH_PASS ") or not match:
        raise ValueError("prior authentic NeXium HP2 pulse ON PASS missing")
    if not (root / "defeat-retry-result.txt").read_text("ascii").startswith(
        "VPD_NEXIUM_DEFEAT_RETRY_PASS "
    ):
        raise ValueError("prior real guard defeat/restart PASS missing")
    records = verify_defeat(
        (root / "guest-live-defeat-retry-witness.txt").read_bytes()
    )
    first, third = source_witness(
        (root / "guest-hd-low-health-witness.txt").read_bytes(), records
    )
    lit_frame = verify_phase(
        (root / "guest-hd-low-health-phase-witness.txt").read_bytes(), third
    )
    if not first < third <= lit_frame < records["death_frame"]:
        raise ValueError("warning event is not in this source-attested combat")
    inputs = (root / "input-probe.txt").read_text("ascii").splitlines()
    for needed in (
        "host_low_hp2_source_seen=yes input=idle",
        "host_low_hp_phase_seen=yes source=live_guest",
        "host_defeat_minus_key_sent=yes key=N expected=Minus",
        "host_defeat_retry_guest_observed=yes",
    ):
        if inputs.count(needed) != 1:
            raise ValueError("native X11 pad or source event not confirmed: " + needed)

    seq = (root / "visual-probe.txt").read_text("ascii").splitlines()
    samples = [f"screen-live-low-hp-{i}" for i in range(3)]
    ordered = samples + ["screen-live-game-over", "screen-live-defeat-restart"]
    try:
        indices = [seq.index("capture=" + label) for label in ordered]
    except ValueError as exc:
        raise ValueError("one of the five native X11 frames is missing") from exc
    if indices != sorted(indices) or len(set(indices)) != len(ordered):
        raise ValueError("real X11 combat/defeat/restart capture order invalid")
    if any(seq.count("capture=" + name) != 1 for name in ordered):
        raise ValueError("duplicate native X11 lifecycle screenshot markers")

    on_id, expected_line, expected_text, expected_sha = match.groups()
    on_id = int(on_id)
    if on_id >= 2:
        raise ValueError("no later source-HP2 screenshot to prove pulse OFF")
    photos = {}
    hashes = {}
    for name in ordered:
        photos[name], hashes[name] = raster(root, name)
    if hashes[samples[on_id]] != expected_sha:
        raise ValueError("the prior independently proven ON frame was replaced")
    # The source pulse must be visibly OFF at a strictly later screenshot,
    # while still at HP2 and BEFORE the real guard kills the actor.
    candidates = []
    for index in range(on_id + 1, 3):
        pixels = photos[samples[index]]
        source_hp2, line, text = hp2_warning(pixels)
        if source_hp2 and line == 0 and text == 0:
            candidates.append(index)
    if not candidates:
        raise ValueError("no later native HP2 screenshot shows pulse OFF")
    off_id = candidates[0]
    on_name, off_name = samples[on_id], samples[off_id]
    death_name, restart_name = ordered[-2:]
    tested = [on_name, off_name, death_name, restart_name]
    if len({hashes[n] for n in tested}) != 4:
        raise ValueError("native lifecycle frames were duplicated or stale")
    counts = verify_lifecycle(
        photos[on_name], photos[off_name], photos[death_name],
        photos[restart_name]
    )
    if (int(expected_line) != counts["warning_line"] or
        int(expected_text) != counts["warning_label"]):
        raise ValueError("prior independently proved ON pixel counts changed")
    result = (
        "VPD_NEXIUM_HD_LOW_HEALTH_LIFECYCLE_PASS "
        f"contact_frame={first} hit_hp2_frame={third} pulse_on_frame={lit_frame} "
        f"death_frame={records['death_frame']} "
        f"on_sample={on_id} off_sample={off_id} "
        f"underline_on_pixels={counts['warning_line']} "
        f"label_on_pixels={counts['warning_label']} "
        "underline_off_pixels=0 label_off_pixels=0 "
        "death_hp=0 restart_hp=5 warning_after_death=no "
        "warning_after_retry=no source_hearts_authentic=yes "
        f"on_ppm_sha256={hashes[on_name]} "
        f"off_ppm_sha256={hashes[off_name]} "
        f"death_ppm_sha256={hashes[death_name]} "
        f"retry_ppm_sha256={hashes[restart_name]} "
        "native_x11_evidence=yes source=libnx_tick "
        "original_game_proven=no physical_switch_proven=no\n"
    )
    (root / "hd-low-health-lifecycle-result.txt").write_text(result, "ascii")
    print(result, end="")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError, ValueError, UnicodeError) as error:
        args.evidence.mkdir(parents=True, exist_ok=True)
        (args.evidence / "hd-low-health-lifecycle-result.txt").write_text(
            "INCONCLUSIVE: " + str(error) + "\n", encoding="ascii")
        parser.exit(1, "NeXium low HP lifecycle unverified: " + str(error) + "\n")
