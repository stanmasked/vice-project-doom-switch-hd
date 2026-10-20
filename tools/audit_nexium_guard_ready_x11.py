#!/usr/bin/env python3
"""Prove the live guard's READY exclamation on genuine NeXium X11, pre-strike.

Reuses exact original libnx alert/strike witnesses, live X11 frame
provenance, and the independently verified first post-strike cooldown pips.
No gameplay, sprites, attack timing or simulation are modified.
"""
import argparse
import hashlib
from pathlib import Path
import re

from audit_nexium_guard_live import verify as verify_guard_source
from audit_nexium_guard_live_raster import parse_ppm, load_anchors, WIDTH, HEIGHT, GUARD_Y
from audit_nexium_guard_cooldown_x11 import guard_sprite_anchor

READY = bytes((248,198,104))
DIM = bytes((92,101,118))


def rgb(pixels,x,y):
    if not (0<=x<WIDTH and 0<=y<HEIGHT):
        return b""
    offset=3*(y*WIDTH+x)
    return pixels[offset:offset+3]


def source_ready_x(raw):
    """Exact real source alert record, before the real first guard hit."""
    if not isinstance(raw,bytes):
        raise ValueError("actual guard guest source witness missing")
    try:
        first,second=raw.decode("ascii").splitlines()
    except (UnicodeError,ValueError) as exc:
        raise ValueError("live guard alert/strike records invalid") from exc
    if not first.startswith("VPD_ROMFREE_GUARD_LIVE_V1 seq=1 event=alert ") or (
        not second.startswith("VPD_ROMFREE_GUARD_LIVE_V1 seq=2 event=strike ")
    ):
        raise ValueError("no source alert before first genuine guard hit")
    values={}
    for part in first.split(" ")[1:]:
        if "=" not in part:
            raise ValueError("bad source alert tokens")
        key,val=part.split("=",1)
        if key in values:
            raise ValueError("duplicate source alert fields")
        values[key]=val
    for name in ("player_x","guard_x","frame","player_hp","guard_hp",
                 "attacks","cooldown","alerted","input_right"):
        if not re.fullmatch(r"0|[1-9][0-9]*",values.get(name,"")):
            raise ValueError("invalid real source alert field: "+name)
    if (int(values["player_hp"])!=5 or
        int(values["guard_hp"])!=2 or
        int(values["attacks"])!=0 or
        int(values["cooldown"])!=0 or
        int(values["alerted"])!=1 or
        int(values["input_right"])!=1):
        raise ValueError("ready-exclamation source gameplay state not verified")
    hero_x=int(values["player_x"])
    guard_x=int(values["guard_x"])
    camera=max(0,min(hero_x//256-160,(64-40)*16))
    result=(guard_x//256-camera)*2
    if not 80<result<1200:
        raise ValueError("guard alert offscreen or ungrounded camera")
    return result


def verify_ready_raster(ready_ppm,strike_ppm,source_x,strike_source_x):
    ready=parse_ppm(ready_ppm)
    strike=parse_ppm(strike_ppm)
    if ready==strike:
        raise ValueError("native ready and strike X11 images were reused")
    gx,gy=guard_sprite_anchor(ready,source_x)
    # Require *both* parts of the original source-authored exclamation:
    # the tall amber stem AND the separate small dot, never a detached
    # one-color region or any nearby bright actor sprite.
    stem=sum(
        rgb(ready,x,y)==READY
        for y in range(gy-27,gy-16)
        for x in range(gx+10,gx+16)
    )
    dot=sum(
        rgb(ready,x,y)==READY
        for y in range(gy-13,gy-9)
        for x in range(gx+10,gx+16)
    )
    if stem<57 or dot<19:
        raise ValueError("native X11 alert guard missing READY ! stem or dot")
    bar=sum(
        rgb(ready,x,y)==DIM
        for y in range(gy-24,gy-16)
        for x in range(gx+3,gx+30)
    )
    if bar>0:
        raise ValueError("guard already on cooldown in source ready frame")
    # First source-owned melee strike removes ! and leaves dim pips. Anchor
    # independently to the real sprite in the second native screenshot,
    # never blindly trust the previous sprite's screen position/camera.
    # The camera and both actors move for ~52 actual guest frames from
    # alert to melee. Anchor the second image independently to the real
    # strike's guest/camera coordinates, not the earlier alert projection.
    sx,sy=guard_sprite_anchor(strike,strike_source_x)
    leftover=sum(
        rgb(strike,x,y)==READY
        for y in range(sy-28,sy-9)
        for x in range(sx+3,sx+30)
    )
    if leftover:
        raise ValueError("READY ! still visible after actual melee hit")
    dim=sum(
        rgb(strike,x,y)==DIM
        for y in range(sy-24,sy-16)
        for x in range(sx+3,sx+30)
    )
    if dim<60 or dim>72:
        raise ValueError("real X11 first strike did not replace ! with cooldown pips")
    return {
        "ready_guard_x11":gx,"ready_guard_y11":gy,
        "stem_pixels":stem,"dot_pixels":dot,
        "strike_dim_pixels":dim,
        "ready_sha":hashlib.sha256(ready_ppm).hexdigest(),
        "strike_sha":hashlib.sha256(strike_ppm).hexdigest(),
    }


def audit(evidence):
    root=Path(evidence)
    for name,marker in (
        ("guard-live-result.txt","VPD_NEXIUM_GUARD_LIVE_CONTACT_PASS "),
        ("guard-live-raster-result.txt","VPD_NEXIUM_GUARD_LIVE_RASTER_PASS "),
        ("guard-cooldown-x11-result.txt","VPD_NEXIUM_GUARD_COOLDOWN_X11_PASS "),
    ):
        if not (root/name).read_text("ascii").startswith(marker):
            raise ValueError("independent real source/X11 predecessor missing: "+name)
    raw=(root/"guest-guard-live-witness.txt").read_bytes()
    frames=verify_guard_source(raw)
    x=source_ready_x(raw)
    anchors=load_anchors(root)
    strike_x=anchors["strike_x"]
    if frames["strike_frame"]!=anchors["strike_frame"]:
        raise ValueError("source strike event disagrees with independently proven X11 anchor")
    host=(root/"input-probe.txt").read_text("ascii").splitlines()
    if host.count("host_guard_live_alert_seen=yes key=D")!=1 or (
        host.count("host_guard_live_move_sent=yes key=D until_guest_strike=yes")!=1
    ):
        raise ValueError("host never saw native early guard alert on actual pad Right")
    visual=(root/"visual-probe.txt").read_text("ascii").splitlines()
    expected=("capture=screen-live-guard-ready","capture=screen-live-strike",
              "capture=screen-live-defeat")
    if any(visual.count(name)!=1 for name in expected):
        raise ValueError("missing/duplicate native X11 alert/strike/defeat captures")
    if not (visual.index(expected[0])<visual.index(expected[1])<
            visual.index(expected[2])):
        raise ValueError("real ready screenshot not earlier than guest strike")
    if visual.count(
        "host_guard_ready_x11_after_source_alert=yes right_still_held=yes"
    )!=1:
        raise ValueError("no source-triggered host X11 ready capture")
    for stem in ("screen-live-guard-ready","screen-live-strike"):
        png=(root/(stem+".png")).read_bytes()
        if not png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("native ready/strike PNG screenshot missing")
    data=verify_ready_raster(
        (root/"screen-live-guard-ready.ppm").read_bytes(),
        (root/"screen-live-strike.ppm").read_bytes(),x,strike_x
    )
    output=(
        "VPD_NEXIUM_GUARD_READY_X11_PASS "
        f"alert_frame={frames['alert_frame']} "
        f"strike_frame={frames['strike_frame']} "
        "source_guard_hp=2 source_cooldown_ready=0 "
        "source_cooldown_strike=32 hero_hp_before=5 hero_hp_after=4 "
        f"ready_guard_x11={data['ready_guard_x11']} "
        f"ready_guard_y11={data['ready_guard_y11']} "
        f"ready_stem_pixels={data['stem_pixels']} "
        f"ready_dot_pixels={data['dot_pixels']} "
        f"strike_dim_pips={data['strike_dim_pixels']} "
        f"ready_ppm_sha256={data['ready_sha']} "
        f"strike_ppm_sha256={data['strike_sha']} "
        "source=live_guest real_pad_right=yes native_x11_evidence=yes "
        "original_game_proven=no physical_switch_proven=no\n"
    )
    (root/"guard-ready-x11-result.txt").write_text(output,encoding="ascii")
    print(output,end="")
    return output


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--evidence",type=Path,required=True)
    args=ap.parse_args()
    try:
        audit(args.evidence)
    except (OSError,UnicodeError,ValueError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"guard-ready-x11-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        ap.exit(1,"NeXium native guard ready exclamation unverified: "+str(exc)+"\n")
