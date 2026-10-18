#!/usr/bin/env python3
"""Strict X11 raster evidence near a guest-authenticated *live* guard death.

Proof scope: an onscreen alert-tinted guard silhouette disappears when the
same native libnx guest records swept-projectile death. It does not attest
exact GPU timings, physical Switch scanout, or original Vice game imagery.
"""
import argparse
import hashlib
from pathlib import Path
import re

WIDTH, HEIGHT = 1280, 720
ALERT_COLOR = bytes((220, 103, 93))  # production guard torso, only if alerted
GUARD_Y = (14 * 16 - 14 + 80) * 2   # renderer's existing synthetic map math


def parse_ppm(blob):
    if not isinstance(blob, bytes) or len(blob) > 3_000_000:
        raise ValueError("capture missing or excessive")
    cursor, tokens = 0, []
    while len(tokens) < 4:
        while cursor < len(blob) and blob[cursor] in b" \t\r\n":
            cursor += 1
        if cursor < len(blob) and blob[cursor] == 35:
            while cursor < len(blob) and blob[cursor] != 10:
                cursor += 1
            continue
        start = cursor
        while cursor < len(blob) and blob[cursor] not in b" \t\r\n":
            cursor += 1
        if start == cursor:
            raise ValueError("truncated P6 header")
        tokens.append(blob[start:cursor])
    if tokens != [b"P6", b"1280", b"720", b"255"]:
        raise ValueError("host X11 capture has unexpected image format")
    if cursor >= len(blob) or blob[cursor] not in b" \t\r\n":
        raise ValueError("no PPM binary payload separator")
    pixels = blob[cursor+1:]
    if len(pixels) != WIDTH * HEIGHT * 3:
        raise ValueError("incorrect P6 pixel payload length")
    return pixels


def _field(row, field):
    match = re.search(r"(?:^| )" + re.escape(field) + r"=(0|[1-9][0-9]*)(?: |$)", row)
    if not match:
        raise ValueError("missing or noncanonical guest coordinate: " + field)
    return int(match.group(1))


def load_anchors(folder):
    contact = (folder / "guest-guard-live-witness.txt").read_text(encoding="ascii").splitlines()
    fight = (folder / "guest-guard-live-defeat-witness.txt").read_text(encoding="ascii").splitlines()
    if (len(contact) != 2 or len(fight) < 2 or
        not contact[1].startswith("VPD_ROMFREE_GUARD_LIVE_V1 seq=2 event=strike ") or
        " event=defeat " not in fight[-1] or
        not fight[-1].startswith("VPD_ROMFREE_GUARD_LIVE_DEFEAT_V1 ")):
        raise ValueError("no linked guest strike/defeat milestones")
    before_frame = _field(contact[1], "frame")
    after_frame = _field(fight[-1], "frame")
    if not before_frame < after_frame <= 1200:
        raise ValueError("guest visual milestones out of order")
    anchors=[]
    for row in (contact[1], fight[-1]):
        hero = _field(row, "player_x")
        guard = _field(row, "guard_x")
        if not (0 <= hero <= 64 * 16 * 256 and 14 * 16 * 256 <= guard <= 20 * 16 * 256):
            raise ValueError("guest position outside ROM-free map")
        camera = max(0, min(hero // 256 - 10 * 16, (64 - 40) * 16))
        # NeXium may pillarbox the 1280-wide game: ±70 covers small offsets,
        # while the lower-sprite ROI excludes GUI performance overlays/HUD.
        cx = (guard // 256 - camera) * 2
        if not 80 < cx < 1200:
            raise ValueError("guard isn't in the visible camera viewport")
        anchors.append(cx)
    return {"strike_frame":before_frame,"defeat_frame":after_frame,
            "strike_x":anchors[0],"defeat_x":anchors[1]}


def count_guard_color(pixels, cx):
    left = max(0, cx - 45)
    right = min(WIDTH, cx + 95)
    top = GUARD_Y - 13
    bottom = GUARD_Y + 41
    count = 0
    palette = set()
    for y in range(top, bottom):
        for x in range(left, right):
            offset = 3 * (y * WIDTH + x)
            pixel = pixels[offset:offset+3]
            if pixel == ALERT_COLOR:
                count += 1
            if (x + y) % 37 == 0:
                palette.add(pixel)
    return count,len(palette)


def evaluate(before, after, anchors):
    b = parse_ppm(before)
    a = parse_ppm(after)
    before_color, color_variants = count_guard_color(b,anchors["strike_x"])
    after_color, _ = count_guard_color(a,anchors["defeat_x"])
    if color_variants < 4:
        raise ValueError("guard-area X11 image suspiciously uniform")
    if before_color < 30:
        raise ValueError("native X11 strike screenshot does not contain alerted guard torso")
    if after_color > 3 or after_color >= before_color // 10:
        raise ValueError("alerted guard silhouette still visible after guest defeat")
    if before == after:
        raise ValueError("host screen did not change")
    return {"guard_pixels_strike":before_color,"guard_pixels_defeat":after_color,
            "strike_sha256":hashlib.sha256(before).hexdigest(),
            "defeat_sha256":hashlib.sha256(after).hexdigest()}


def audit(folder):
    root=Path(folder)
    visual_marker=root/"visual-probe.txt"
    if not visual_marker.is_file():
        raise ValueError("real X11 event-aligned screenshots absent")
    progress=visual_marker.read_text(encoding="ascii").splitlines()
    if not all(marker in progress for marker in (
        "visual_probe=finished",
        "capture=screen-live-strike",
        "capture=screen-live-defeat",
        "live_raster_strike_after_guest_event=yes",
        "live_raster_defeat_after_guest_event=yes",
    )):
        raise ValueError("real X11 event-aligned screenshots absent")
    host=(root/"input-probe.txt").read_text(encoding="ascii").splitlines()
    if ("host_guard_live_defeat_observed=yes" not in host or
        "host_guard_live_fire_sent=yes key=Z after_guest_strike=yes" not in host):
        raise ValueError("host did not observe guest death before final screenshot")
    for name,prefix in (
        ("guard-live-result.txt","VPD_NEXIUM_GUARD_LIVE_CONTACT_PASS "),
        ("guard-live-defeat-result.txt","VPD_NEXIUM_GUARD_LIVE_DEFEAT_PASS "),
        ("native-exit-result.txt","VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
        ("visual-result.txt","VPD_NEXIUM_VISUAL_FRAME_PASS "),
    ):
        path=root/name
        if not path.is_file() or not path.read_text(encoding="ascii").startswith(prefix):
            raise ValueError("independent NeXium prerequisite missing: "+name)
    anchors=load_anchors(root)
    for label in ("strike","defeat"):
        png=root/("screen-live-"+label+".png")
        if not png.is_file() or not png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("real X11 PNG capture missing: "+label)
    before=(root/"screen-live-strike.ppm").read_bytes()
    after=(root/"screen-live-defeat.ppm").read_bytes()
    result=evaluate(before,after,anchors)
    report=(
        "VPD_NEXIUM_GUARD_LIVE_RASTER_PASS "
        f"strike_frame={anchors['strike_frame']} "
        f"defeat_frame={anchors['defeat_frame']} "
        f"guard_pixels_strike={result['guard_pixels_strike']} "
        f"guard_pixels_defeat={result['guard_pixels_defeat']} "
        f"strike_ppm_sha256={result['strike_sha256']} "
        f"defeat_ppm_sha256={result['defeat_sha256']} "
        "native_x11_evidence=yes guest_manual_kill=yes "
        "physical_scanout_proven=no original_game_proven=no\n"
    )
    (root/"guard-live-raster-result.txt").write_text(report,encoding="ascii")
    print(report,end="")
    return result

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--evidence",type=Path,required=True)
    args=ap.parse_args()
    try:
        audit(args.evidence)
    except (OSError,ValueError,UnicodeError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"guard-live-raster-result.txt").write_text("INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        ap.exit(1,"NeXium manual guard pixels unverified: "+str(exc)+"\n")
