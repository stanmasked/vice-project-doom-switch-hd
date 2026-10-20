#!/usr/bin/env python3
"""Fail-closed native NeXium X11 proof that authentic guard HP2 draws LOW HP."""
import argparse
from pathlib import Path
import re

from audit_nexium_defeat_retry import verify as verify_defeat
from audit_nexium_fourth_stage import raster
from audit_nexium_hd_fx_sentry_hit import LIVE_HEART_RECTS, FIFTH_HEART_RECT

WIDTH = 1280
HEIGHT = 720
PREFIX = b"VPD_HD_LOW_HEALTH_GUEST_V1 "
RECORD = re.compile(
    rb"^VPD_HD_LOW_HEALTH_GUEST_V1 contact_frame=(0|[1-9][0-9]*) "
    rb"frame=(0|[1-9][0-9]*) hero_hp_before=3 hero_hp_after=2 "
    rb"guard_attacks_before=2 guard_attacks_after=3 "
    rb"input=idle hd=on guard_hp=3 wave=0 clear=0 "
    rb"source=libnx_tick original_game_proven=no\n$"
)
PHASE = re.compile(
    rb"^VPD_HD_LOW_HEALTH_PHASE_V1 third_frame=(0|[1-9][0-9]*) "
    rb"frame=(0|[1-9][0-9]*) hero_hp=2 guard_attacks=3 "
    rb"input=idle hd=on pulse=on source=libnx_tick "
    rb"original_game_proven=no\n$"
)
TEAL = bytes((106, 198, 174))
FLASH = bytes((255, 220, 153))
EMPTY = bytes((55, 64, 79))
WARNING = bytes((237, 115, 112))
LABEL = bytes((255, 171, 147))

def source_witness(raw, defeat):
    """Tie native HP2 to the SAME first guard contact and later real death."""
    if not isinstance(raw, bytes) or len(raw) > 380 or not RECORD.fullmatch(raw):
        raise ValueError("invalid/duplicate/missing source-owned HP2 guard witness")
    m = RECORD.fullmatch(raw)
    contact, third = map(int, m.groups())
    if (contact != defeat["contact_frame"] or
        third != contact + 64 or
        defeat["death_frame"] != third + 64):
        raise ValueError("HP2 event not 2 genuine 32-tick strikes after contact")
    return contact, third

def verify_phase(raw, third):
    """Only real source frame 0 mod 24 may trigger a pulse-on capture."""
    if not isinstance(raw, bytes) or len(raw) > 380:
        raise ValueError("native LOW HP phase witness missing/oversized")
    match = PHASE.fullmatch(raw)
    if not match:
        raise ValueError("source LOW HP ON half-cycle not verified")
    recorded_third, lit_frame = map(int, match.groups())
    if (recorded_third != third or lit_frame % 24 != 0 or
        not third <= lit_frame < third + 32):
        raise ValueError("LOW HP ON phase not tied to live HP2 third strike")
    return lit_frame

def count_color(image, rect, color):
    x0, y0, x1, y1 = rect
    count = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            ix = (y * WIDTH + x) * 3
            count += image[ix:ix+3] == color
    return count

def hp2_warning(image):
    """Count true hearts and optional LIVE warning only in fixed HUD ROIs."""
    if len(image) != WIDTH * HEIGHT * 3:
        raise ValueError("not a native full-resolution NeXium RGB frame")
    hearts = []
    # Native NeXium guest pixels differ from untransformed renderer
    # coords by 4–5 px at this HUD. Reuse THE SAME independent X11
    # heart chip rectangles already proved for live sentry damage.
    rects = (*LIVE_HEART_RECTS, FIFTH_HEART_RECT)
    for left, right in rects:
        roi = (left, 17, right+1, 29)
        healthy = count_color(image, roi, TEAL) + count_color(image, roi, FLASH)
        dark = count_color(image, roi, EMPTY)
        hearts.append((healthy, dark))
    # Require precisely 2 occupied chips and 3 empty source cells; never
    # count a label painted over the HUD as proof of authentic damage.
    source_hp2 = (all(h >= 110 and e == 0 for h, e in hearts[:2]) and
                  all(e >= 110 and h == 0 for h, e in hearts[2:]))
    # Include native X11 presentation padding and the -4 px window
    # offset; exact authored colors distinguish these from other HUD.
    underline = count_color(image, (747, 29, 843, 42), WARNING)
    text = count_color(image, (832, 11, 954, 39), LABEL)
    return source_hp2, underline, text

def audit(evidence):
    base = Path(evidence)
    previous = (base/"defeat-retry-result.txt").read_text("ascii")
    if not previous.startswith("VPD_NEXIUM_DEFEAT_RETRY_PASS "):
        raise ValueError("earlier real pad victory, defeat and retry not proved")
    defeat = verify_defeat((base/"guest-live-defeat-retry-witness.txt").read_bytes())
    contact, third = source_witness(
        (base/"guest-hd-low-health-witness.txt").read_bytes(), defeat)
    on_phase = verify_phase(
        (base/"guest-hd-low-health-phase-witness.txt").read_bytes(), third)
    host = (base/"input-probe.txt").read_text("ascii").splitlines()
    if host.count("host_low_hp2_source_seen=yes input=idle") != 1 or (
        "host_post_victory_guard_contact_sent=yes key=D observed=yes" not in host
    ):
        raise ValueError("host did not wait for real idle third melee strike")
    if host.count("host_low_hp_phase_seen=yes source=live_guest") != 1:
        raise ValueError("host did not wait for native HP2 pulse ON marker")
    timeline = (base/"visual-probe.txt").read_text("ascii").splitlines()
    if timeline.count("host_low_hp_x11_samples=3 source=real_guard_hit") != 1:
        raise ValueError("host source-aligned HP2 screenshots absent")
    screenshots = ["screen-live-low-hp-"+str(i) for i in range(3)]
    for name in screenshots:
        if timeline.count("capture="+name) != 1:
            raise ValueError("missing/duplicate genuine HP2 capture: "+name)
    death_image = timeline.index("capture=screen-live-game-over")
    if any(timeline.index("capture="+name) >= death_image for name in screenshots):
        raise ValueError("HP2 screenshot happened after the guest death screen")

    good = []
    snapshots = []
    for i, name in enumerate(screenshots):
        pixels, sha = raster(base, name)
        active, underline, label = hp2_warning(pixels)
        snapshots.append((i, sha, active, underline, label))
        if active and underline >= 180 and label >= 40:
            good.append((i, sha, underline, label))
    if not good:
        raise ValueError("no real native X11 HP2 frame shows the LOW HP warning")
    index, sha, underline, label = good[0]
    result = (
        "VPD_NEXIUM_HD_LOW_HEALTH_PASS "
        f"contact_frame={contact} third_strike_frame={third} "
        f"source_on_frame={on_phase} "
        "hero_hp=2 guard_attacks=3 guard_cooldown=32 "
        f"live_x11_sample={index} underline_pixels={underline} "
        f"label_pixels={label} ppm_sha256={sha} "
        "two_healthy_hearts=yes three_empty_hearts=yes "
        "real_idle_guard_hit=yes hd_fx_enabled=yes "
        "source=libnx_tick native_x11_evidence=yes "
        "original_game_proven=no physical_switch_proven=no\n"
    )
    (base/"hd-low-health-result.txt").write_text(result, encoding="ascii")
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
        (args.evidence/"hd-low-health-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n", encoding="ascii")
        parser.exit(1,"NeXium real source HP2 HUD warning unverified: "+str(exc)+"\n")
