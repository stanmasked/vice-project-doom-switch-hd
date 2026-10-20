#!/usr/bin/env python3
"""Fail-closed X11 proof that an authentic turret hit flashes the HERO, not only the HUD."""
import argparse
from pathlib import Path
import re

from audit_nexium_fourth_stage import raster
from audit_nexium_hd_fx_sentry import verify as verify_sentry
from audit_nexium_hd_fx_sentry_hit import verify as verify_hit

WIDTH, HEIGHT = 1280, 720
HERO_ROI = (300, 538, 420, 610)  # measured native NeXium X11; excludes HUD/sentry
JACKET = (164, 51, 68)            # unchanged authored hero torso
FACE = (220, 179, 137)            # unchanged authored hero face
CHEST_FLASH = (255, 220, 153)     # authored 22x4 hit-only stripe
HEAD_FLASH = (252, 180, 119)      # authored 27x2 hit-only stripe
SHA = re.compile(r" before_ppm_sha256=([0-9a-f]{64}) after_ppm_sha256=([0-9a-f]{64}) ")

def pixels_for(raw, color):
    """Find an exact RGB color only in the lower-screen actor, never the HUD."""
    x0, y0, x1, y1 = HERO_ROI
    ink = bytes(color)
    return {(x, y) for y in range(y0, y1) for x in range(x0, x1)
            if raw[(y * WIDTH + x) * 3:(y * WIDTH + x) * 3 + 3] == ink}

def bounds(points):
    return (min(x for x, _ in points), max(x for x, _ in points),
            min(y for _, y in points), max(y for _, y in points))

def hero_impact_pixels(before, after):
    """Require both hit-only stripes on the SAME stable source-owned hero."""
    if len(before) != WIDTH * HEIGHT * 3 or len(after) != len(before):
        raise ValueError("real NeXium X11 impact screenshot not 1280x720 RGB")
    same_jacket = pixels_for(before, JACKET) & pixels_for(after, JACKET)
    same_face = pixels_for(before, FACE) & pixels_for(after, FACE)
    if len(same_jacket) < 230 or len(same_face) < 225:
        raise ValueError("same original hero jacket/face not present before and after hit")
    if pixels_for(before, CHEST_FLASH) or pixels_for(before, HEAD_FLASH):
        raise ValueError("hero impact stripes already present before source bullet hit")
    chest = pixels_for(after, CHEST_FLASH)
    head = pixels_for(after, HEAD_FLASH)
    if not 80 <= len(chest) <= 96 or not 48 <= len(head) <= 56:
        raise ValueError("both independent hero impact stripes not present after hit")
    cx0, cx1, cy0, cy1 = bounds(chest)
    hx0, hx1, hy0, hy1 = bounds(head)
    jx0, jx1, _, _ = bounds(same_jacket)
    if not (21 <= cx1-cx0+1 <= 23 and cy1-cy0+1 == 4 and
            24 <= hx1-hx0+1 <= 28 and hy1-hy0+1 == 2 and
            14 <= cy0-hy1 <= 26 and
            abs((cx0+cx1)-(hx0+hx1)) <= 16 and
            jx0-12 <= cx0 <= jx1 and jx0-14 <= hx0 <= jx1 and
            hx1 <= jx1+3 and cx1 <= jx1+3):
        raise ValueError("impact stripe shape/location not aligned with same live hero")
    if any(sum((x, y) in chest for x in range(cx0, cx1+1)) < 20
           for y in range(cy0, cy1+1)):
        raise ValueError("chest impact stripe has broken rows")
    if any(sum((x, y) in head for x in range(hx0, hx1+1)) < 24
           for y in range(hy0, hy1+1)):
        raise ValueError("head impact stripe has broken rows")
    return len(chest), len(head), len(same_jacket), len(same_face)

def audit(folder):
    base = Path(folder)
    prior = (base / "hd-fx-sentry-hit-result.txt").read_text("ascii")
    if not prior.startswith("VPD_NEXIUM_HD_FX_SENTRY_HIT_PASS "):
        raise ValueError("actual projectile hit plus health HUD proof absent")
    off, on = verify_sentry((base / "guest-hd-fx-sentry-witness.txt").read_bytes())
    hit = verify_hit((base / "guest-hd-fx-sentry-hit-witness.txt").read_bytes(), on)
    if not off["frame"] < on["frame"] < hit["frame"]:
        raise ValueError("hero visual proof lacks real OFF/ON and later hit")
    before, before_sha = raster(base, "screen-live-sentry-hd-fx-on")
    after, after_sha = raster(base, "screen-live-sentry-after-hit")
    hashes = SHA.search(prior)
    if not hashes or hashes.groups() != (before_sha, after_sha):
        raise ValueError("hero X11 image hashes do not match the live collision audit")
    chest, head, jacket, face = hero_impact_pixels(before, after)
    result = (
        "VPD_NEXIUM_SENTRY_HERO_IMPACT_PASS "
        f"on_frame={on['frame']} hit_frame={hit['frame']} "
        f"hero_hp_before={hit['hero_hp_before']} hero_hp_after={hit['hero_hp_after']} "
        f"chest_flash_pixels={chest} head_flash_pixels={head} "
        f"unchanged_hero_jacket_pixels={jacket} unchanged_hero_face_pixels={face} "
        f"before_ppm_sha256={before_sha} after_ppm_sha256={after_sha} "
        "actual_hostile_collision=yes source=libnx_tick native_x11_evidence=yes "
        "original_game_proven=no physical_switch_proven=no\n"
    )
    (base / "sentry-hero-impact-result.txt").write_text(result, encoding="ascii")
    print(result, end="")
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError, UnicodeError, ValueError) as exc:
        args.evidence.mkdir(parents=True, exist_ok=True)
        (args.evidence / "sentry-hero-impact-result.txt").write_text(
            "INCONCLUSIVE: " + str(exc) + "\n", encoding="ascii")
        parser.exit(1, "Real hero impact X11 evidence unverified: " + str(exc) + "\n")
