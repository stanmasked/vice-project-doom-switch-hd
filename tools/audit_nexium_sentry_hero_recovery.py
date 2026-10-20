#!/usr/bin/env python3
"""Fail-closed proof the first real sentry hit's 16-tick actor flash expires."""
import argparse
from pathlib import Path
import re

from audit_nexium_fourth_stage import raster
from audit_nexium_hd_fx_sentry import verify as verify_sentry
from audit_nexium_hd_fx_sentry_hit import (
    verify as verify_hit, fifth_heart_loss,
)
from audit_nexium_sentry_hero_impact import (
    hero_impact_pixels, pixels_for, JACKET, FACE, CHEST_FLASH, HEAD_FLASH,
)

RECORD = re.compile(
    r"^VPD_HD_FX_SENTRY_RECOVER_V1 hit_frame=([0-9]+) "
    r"frame=([0-9]+) flash_before=1 flash_after=0 "
    r"hero_hp_before=([1-5]) hero_hp_after=([1-5]) "
    r"hero_x=([0-9]+) hero_y=([0-9]+) shots_hit=([0-9]+) "
    r"mode=on input=idle wave=1 guard_hp=0 sentry_hp=2 "
    r"source=libnx_tick original_game_proven=no$"
)
SHA = re.compile(
    r"before_ppm_sha256=([0-9a-f]{64}) "
    r"after_ppm_sha256=([0-9a-f]{64})"
)

def verify_recovery(raw, hit):
    if not isinstance(raw, bytes) or len(raw) > 450 or not raw.endswith(b"\n"):
        raise ValueError("guest flash recovery witness missing/truncated/oversized")
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeError as exc:
        raise ValueError("guest flash recovery witness not ASCII") from exc
    if len(lines) != 1:
        raise ValueError("exactly one native source flash expiry required")
    match = RECORD.fullmatch(lines[0])
    if not match:
        raise ValueError("native source flash expiry record invalid")
    first, last, hp_before, hp_after, hero_x, hero_y, shots = map(int, match.groups())
    if (first != hit["frame"] or last != first + 16 or
        hp_before != hit["hero_hp_after"] or hp_after != hp_before or
        hero_x != hit["hero_x"] or hero_y != hit["hero_y"] or
        shots != hit["shots_hit_after"]):
        raise ValueError("hero flash recovery not same stable 16-tick collision")
    return dict(hit_frame=first, frame=last, hp=hp_after,
                hero_x=hero_x, hero_y=hero_y, shots_hit=shots)

def recovered_actor_pixels(before, impact, recovered):
    # The already independently proved actor flash must exist at the impact
    # frame, then completely disappear at recovery. Unchanged hero pixels
    # prevent a shifted/off-screen actor from appearing to have recovered.
    hero_impact_pixels(before, impact)
    same_jacket = pixels_for(before, JACKET) & pixels_for(recovered, JACKET)
    same_face = pixels_for(before, FACE) & pixels_for(recovered, FACE)
    if len(same_jacket) < 230 or len(same_face) < 225:
        raise ValueError("recovered actor no longer at original jacket/face")
    if pixels_for(recovered, CHEST_FLASH) or pixels_for(recovered, HEAD_FLASH):
        raise ValueError("hit-only hero flash remains visible after source expiry")
    healthy_loss = fifth_heart_loss(before, recovered)
    return healthy_loss, len(same_jacket), len(same_face)

def audit(folder):
    base = Path(folder)
    prior_hit = (base / "hd-fx-sentry-hit-result.txt").read_text("ascii")
    prior_hero = (base / "sentry-hero-impact-result.txt").read_text("ascii")
    if not prior_hit.startswith("VPD_NEXIUM_HD_FX_SENTRY_HIT_PASS ") or not (
        prior_hero.startswith("VPD_NEXIUM_SENTRY_HERO_IMPACT_PASS ")):
        raise ValueError("prior genuine bullet hit and actor X11 flash not verified")
    _, on = verify_sentry((base / "guest-hd-fx-sentry-witness.txt").read_bytes())
    hit = verify_hit((base / "guest-hd-fx-sentry-hit-witness.txt").read_bytes(), on)
    recovery = verify_recovery(
        (base / "guest-hd-fx-sentry-recover-witness.txt").read_bytes(), hit)
    host = (base / "input-probe.txt").read_text("ascii").splitlines()
    visual = (base / "visual-probe.txt").read_text("ascii").splitlines()
    if host.count("host_sentry_hero_recovery_observed=yes source=live_guest") != 1:
        raise ValueError("host never observed real source expiry")
    if (visual.count("capture=screen-live-sentry-after-recovery") != 1 or
        visual.count("live_sentry_recovery_raster_after_guest_event=yes") != 1):
        raise ValueError("fresh X11 recovery screenshot chronology missing")
    before, sha_before = raster(base, "screen-live-sentry-hd-fx-on")
    impact, sha_impact = raster(base, "screen-live-sentry-after-hit")
    recovered, sha_recovered = raster(base, "screen-live-sentry-after-recovery")
    earlier = SHA.search(prior_hero)
    old = SHA.search(prior_hit)
    if (not earlier or not old or earlier.groups() != old.groups() or
        earlier.groups() != (sha_before, sha_impact) or
        sha_recovered in (sha_before, sha_impact)):
        raise ValueError("recovery X11 frames do not chain to same real hit")
    fifth, jacket, face = recovered_actor_pixels(before, impact, recovered)
    result = (
        "VPD_NEXIUM_SENTRY_HERO_RECOVERY_PASS "
        f"hit_frame={recovery['hit_frame']} recovery_frame={recovery['frame']} "
        "flash_ticks=16 flash_before=1 flash_after=0 "
        f"hero_hp_after={recovery['hp']} shots_hit={recovery['shots_hit']} "
        "chest_flash_cleared=yes head_flash_cleared=yes "
        f"fifth_heart_still_empty_pixels={fifth} "
        f"same_hero_jacket_pixels={jacket} same_hero_face_pixels={face} "
        f"impact_ppm_sha256={sha_impact} recovery_ppm_sha256={sha_recovered} "
        "source=libnx_tick native_x11_evidence=yes "
        "original_game_proven=no physical_switch_proven=no\n"
    )
    (base / "sentry-hero-recovery-result.txt").write_text(
        result, encoding="ascii")
    print(result, end="")
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError, ValueError, UnicodeError) as error:
        args.evidence.mkdir(parents=True, exist_ok=True)
        (args.evidence / "sentry-hero-recovery-result.txt").write_text(
            "INCONCLUSIVE: " + str(error) + "\n", encoding="ascii")
        parser.exit(1, "Sentry hero recovery X11 proof unverified: " + str(error) + "\n")
