#!/usr/bin/env python3
"""Strict source-attested NeXium X11 proof of the guard's post-strike dim pips.

Reuses two independently authenticated REAL guest/X11 screenshots. The
previous host raster test already proves ready (!) and refill at cooldown 20;
this separate native test attests visible pips at first actual contact and
their disappearance after the SAME guard is legitimately shot down.
"""
import argparse
import hashlib
from pathlib import Path

from audit_nexium_guard_live import verify as verify_guard_source
from audit_nexium_guard_live_raster import (
    parse_ppm, load_anchors, WIDTH, HEIGHT, GUARD_Y,
)

BASE = bytes((65, 76, 94))
FACE = bytes((194, 110, 92))
HP = bytes((247, 175, 96))
DIM = bytes((92, 101, 118))
READY = bytes((248, 198, 104))


def color(pixels, x, y):
    if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
        return b""
    pos = 3 * (y * WIDTH + x)
    return pixels[pos:pos+3]


def guard_sprite_anchor(pixels, source_x):
    """Find the genuine guard torso + TWO surviving source HP pips.

    Do not allow a detached three-bar doodle to count as a real source guard.
    X11 screen coordinates have a modest Vulkan viewport offset; search
    only near the source/camera-projected x and fixed guard ground height.
    """
    if len(pixels) != WIDTH * HEIGHT * 3 or not (80 < source_x < 1200):
        raise ValueError("not a real native guard viewport")
    hits = []
    for y in range(GUARD_Y - 40, GUARD_Y + 24):
        for x in range(max(90,source_x-45), min(WIDTH-35,source_x+45)):
            if (color(pixels,x+2,y-7)==HP and
                color(pixels,x+10,y-7)==HP and
                color(pixels,x+3,y+3)==BASE and
                color(pixels,x+10,y+4)==FACE):
                hits.append((x,y))
    if not hits:
        raise ValueError("no real guarded sprite beneath threatened marker")
    xs,ys=zip(*hits)
    if max(xs)-min(xs)>3 or max(ys)-min(ys)>3:
        raise ValueError("ambiguous synthetic guard sprite location")
    return min(xs), min(ys)


def verify_cooldown_raster(before, after, anchors):
    first = parse_ppm(before)
    last = parse_ppm(after)
    gx,gy = guard_sprite_anchor(first, anchors["strike_x"])
    if first == last:
        raise ValueError("reused a single X11 frame for strike and guard death")
    # All 3 dim pips on a single actual melee strike. Tolerate the genuine
    # X11 viewport displacement via exact source actor sprite anchoring,
    # not by broadening colors or accepting any nearby gray bars.
    for n in range(3):
        x = gx+5+8*n
        for yy in (gy-21,gy-20):
            if color(first,x,yy)!=DIM:
                raise ValueError("real guard strike missing dim cooldown pip")
    dim_pixels=sum(
        color(first,x,y)==DIM
        for y in range(gy-24,gy-16)
        for x in range(gx+3,gx+30)
    )
    if not (60 <= dim_pixels <= 72):
        raise ValueError("cooldown pips missing, repainted or forged on X11")
    if any(color(first,x,y)==READY for y in range(gy-28,gy-9)
           for x in range(gx+2,gx+30)):
        raise ValueError("guard incorrectly remained attack-ready after strike")

    # Same dead guard's source-camera projected location. The exact
    # cooldown-specific glyph colors must vanish, never persist ghosted.
    dx=anchors["defeat_x"]
    dim_after=0
    for y in range(GUARD_Y-42,GUARD_Y+4):
        for x in range(max(0,dx-48),min(WIDTH,dx+95)):
            if color(last,x,y)==DIM:
                dim_after+=1
    if dim_after:
        raise ValueError("guard cooldown threat indicator persisted after kill")
    return {
        "source_guard_x11":gx,
        "source_guard_y11":gy,
        "cooldown_dim_pixels":dim_pixels,
        "post_defeat_dim_pixels":dim_after,
        "strike_sha":hashlib.sha256(before).hexdigest(),
        "defeat_sha":hashlib.sha256(after).hexdigest(),
    }


def audit(evidence):
    root=Path(evidence)
    for filename,marker in (
        ("guard-live-result.txt","VPD_NEXIUM_GUARD_LIVE_CONTACT_PASS "),
        ("guard-live-defeat-result.txt","VPD_NEXIUM_GUARD_LIVE_DEFEAT_PASS "),
        ("guard-live-raster-result.txt","VPD_NEXIUM_GUARD_LIVE_RASTER_PASS "),
    ):
        if not (root/filename).read_text("ascii").startswith(marker):
            raise ValueError("required prior native source/X11 PASS absent: "+filename)
    source=verify_guard_source((root/"guest-guard-live-witness.txt").read_bytes())
    anchors=load_anchors(root)
    if (source["strike_frame"]!=anchors["strike_frame"] or
        not source["alert_frame"]<source["strike_frame"]<anchors["defeat_frame"]):
        raise ValueError("guard cue not tied to real alert/strike/defeat timeline")
    host=(root/"input-probe.txt").read_text("ascii").splitlines()
    if (host.count("host_guard_live_move_sent=yes key=D until_guest_strike=yes")!=1 or
        host.count("host_guard_live_defeat_observed=yes")!=1):
        raise ValueError("physical Right and later first-guard defeat unproven")
    timeline=(root/"visual-probe.txt").read_text("ascii").splitlines()
    for item in ("capture=screen-live-strike","capture=screen-live-defeat"):
        if timeline.count(item)!=1:
            raise ValueError("genuine source-aligned native X11 marker missing")
    if timeline.index("capture=screen-live-strike")>=timeline.index(
        "capture=screen-live-defeat"
    ):
        raise ValueError("native X11 cooldown and death frames out of order")
    for label in ("strike","defeat"):
        path=root/("screen-live-"+label+".png")
        if not path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("real NeXium PNG companion absent: "+label)
    a=(root/"screen-live-strike.ppm").read_bytes()
    b=(root/"screen-live-defeat.ppm").read_bytes()
    values=verify_cooldown_raster(a,b,anchors)
    result=(
        "VPD_NEXIUM_GUARD_COOLDOWN_X11_PASS "
        f"alert_frame={source['alert_frame']} "
        f"strike_frame={source['strike_frame']} "
        f"defeat_frame={anchors['defeat_frame']} "
        "hero_hp_after_melee=4 source_cooldown=32 "
        f"guard_x11={values['source_guard_x11']} "
        f"guard_y11={values['source_guard_y11']} "
        f"three_dim_pips_x11={values['cooldown_dim_pixels']} "
        f"pips_after_guard_death={values['post_defeat_dim_pixels']} "
        f"strike_ppm_sha256={values['strike_sha']} "
        f"defeat_ppm_sha256={values['defeat_sha']} "
        "source=live_guest real_pad_right=yes "
        "native_x11_evidence=yes original_game_proven=no "
        "physical_switch_proven=no\n"
    )
    (root/"guard-cooldown-x11-result.txt").write_text(result,"ascii")
    print(result,end="")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    opts=parser.parse_args()
    try:
        audit(opts.evidence)
    except (OSError,UnicodeError,ValueError) as exc:
        opts.evidence.mkdir(parents=True,exist_ok=True)
        (opts.evidence/"guard-cooldown-x11-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n","ascii")
        parser.exit(1,"NeXium guard cooldown pips unverified: "+str(exc)+"\n")
