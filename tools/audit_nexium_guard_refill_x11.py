#!/usr/bin/env python3
"""Fail-closed source/X11 proof of real guard melee cooldown refilling at 20.

The original ROM-free guest must produce a genuine first melee source hit
and independently record 12 untouched idle ticks (32 -> 20 cooldown).
A real X11 photo must then show one amber and two still-dim guard pips.
"""
import argparse
import hashlib
from pathlib import Path
import re

from audit_nexium_guard_live import verify as verify_live
from audit_nexium_guard_live_raster import parse_ppm, WIDTH, HEIGHT
from audit_nexium_guard_cooldown_x11 import (
    guard_sprite_anchor, verify_cooldown_raster,
)

WARM = bytes((237,170,101))
DIM = bytes((92,101,118))
READY = bytes((248,198,104))
MARKER = re.compile(
    rb"^VPD_GUARD_COOLDOWN_REFILL_V1 "
    rb"strike_frame=(0|[1-9][0-9]*) frame=(0|[1-9][0-9]*) "
    rb"hero_x=(0|[1-9][0-9]*) guard_x=(0|[1-9][0-9]*) "
    rb"camera_x=(0|[1-9][0-9]*) "
    rb"hero_hp=4 guard_hp=2 attacks=1 cooldown=20 input=idle hd=on "
    rb"source=libnx_tick original_game_proven=no\n$"
)


def witness(raw, guard_events):
    if not isinstance(raw,bytes) or len(raw)>350:
        raise ValueError("missing, duplicate or excessive native cooldown record")
    m=MARKER.fullmatch(raw)
    if not m:
        raise ValueError("invalid genuine native 32-to-20 guard cooldown schema")
    strike, frame, hero_x, guard_x, cam_x=map(int,m.groups())
    if strike!=guard_events["strike_frame"] or frame!=strike+12:
        raise ValueError("refill was not 12 real idle ticks after first melee")
    if not (0<=hero_x<=64*16*256 and
            14*16*256<=guard_x<=20*16*256 and
            0<=cam_x<=64*16):
        raise ValueError("native guard/camera coordinates invalid")
    projected=(guard_x//256-cam_x)*2
    if not 80<projected<1200:
        raise ValueError("source guard refill outside native camera viewport")
    return {"strike_frame":strike,"frame":frame,
            "projected_x":projected,"hero_x":hero_x,
            "guard_x":guard_x}


def pixels(frame,x,y):
    if not (0<=x<WIDTH and 0<=y<HEIGHT):
        return b""
    i=3*(y*WIDTH+x)
    return frame[i:i+3]


def verify_refill_raster(before_ppm,refill_ppm,refill_x):
    old=parse_ppm(before_ppm)
    new=parse_ppm(refill_ppm)
    if old==new:
        raise ValueError("first-strike and 12-tick refill X11 frames identical")
    gx,gy=guard_sprite_anchor(new,refill_x)
    # New source display after 12 actual ticks: elapsed=12, floor(12*3/32)
    # = 1 lit bar. Identical six-by-four authored source pixels become
    # bounded native X11 colors anchored to its real guard HP/body.
    bars=[]
    for i in range(3):
        x0=gx+5+8*i
        region=[pixels(new,x,y)
                for y in range(gy-22,gy-18)
                for x in range(x0,x0+6)]
        bars.append({
            "warm":sum(c==WARM for c in region),
            "dim":sum(c==DIM for c in region),
        })
    if not (bars[0]["warm"]>=18 and bars[0]["dim"]==0 and
            all(b["dim"]>=18 and b["warm"]==0 for b in bars[1:])):
        raise ValueError("real guard cooldown did not refill precisely one pip")
    # The exclamation marker must not reappear while cooldown is nonzero.
    if any(pixels(new,x,y)==READY for y in range(gy-28,gy-9)
           for x in range(gx+2,gx+30)):
        raise ValueError("READY ! illegally reappeared during guard cooldown")
    warm=sum(b["warm"] for b in bars)
    dim=sum(b["dim"] for b in bars)
    if warm>24 or dim>48:
        raise ValueError("source cooldown color leaked beyond three native pips")
    return {"gx":gx,"gy":gy,"warm":warm,"dim":dim,
            "before_sha":hashlib.sha256(before_ppm).hexdigest(),
            "refill_sha":hashlib.sha256(refill_ppm).hexdigest()}


def audit(path):
    root=Path(path)
    for name,prefix in (
        ("guard-live-result.txt","VPD_NEXIUM_GUARD_LIVE_CONTACT_PASS "),
        ("guard-cooldown-x11-result.txt","VPD_NEXIUM_GUARD_COOLDOWN_X11_PASS "),
        ("guard-ready-x11-result.txt","VPD_NEXIUM_GUARD_READY_X11_PASS "),
    ):
        if not (root/name).read_text("ascii").startswith(prefix):
            raise ValueError("original source/X11 prior guard PASS absent: "+name)
    events=verify_live((root/"guest-guard-live-witness.txt").read_bytes())
    data=witness((root/"guest-guard-cooldown-refill-witness.txt").read_bytes(),events)
    host=(root/"input-probe.txt").read_text("ascii").splitlines()
    if (host.count("host_guard_cooldown20_source_seen=yes input=idle")!=1 or
        host.count("host_guard_live_move_sent=yes key=D until_guest_strike=yes")!=1):
        raise ValueError("real native source cooldown or player input missing")
    visual=(root/"visual-probe.txt").read_text("ascii").splitlines()
    marks=["capture=screen-live-strike","capture=screen-live-guard-refill",
           "capture=screen-live-defeat"]
    if any(visual.count(m)!=1 for m in marks):
        raise ValueError("native guard strike/refill/defeat X11 frames missing")
    if not (visual.index(marks[0])<visual.index(marks[1])<visual.index(marks[2])):
        raise ValueError("native guard cooldown X11 capture order invalid")
    if visual.count("host_guard_refill_x11_after_source_cooldown=yes")!=1:
        raise ValueError("refill X11 capture not triggered by genuine source")
    for stem in ("screen-live-strike","screen-live-guard-refill"):
        if not (root/(stem+".png")).read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("source-related real NeXium PNG missing: "+stem)
    result=verify_refill_raster(
        (root/"screen-live-strike.ppm").read_bytes(),
        (root/"screen-live-guard-refill.ppm").read_bytes(),
        data["projected_x"],
    )
    stamp=(
        "VPD_NEXIUM_GUARD_COOLDOWN_REFILL_X11_PASS "
        f"strike_frame={data['strike_frame']} "
        f"refill_frame={data['frame']} cooldown_32_to_20=yes "
        "hero_hp=4 guard_hp=2 source_input=idle "
        "three_pips=one_lit_two_dim "
        f"lit_pixels={result['warm']} dim_pixels={result['dim']} "
        f"refill_guard_x11={result['gx']} refill_guard_y11={result['gy']} "
        f"strike_ppm_sha256={result['before_sha']} "
        f"refill_ppm_sha256={result['refill_sha']} "
        "source=libnx_tick native_x11_evidence=yes "
        "original_game_proven=no physical_switch_proven=no\n"
    )
    (root/"guard-cooldown-refill-x11-result.txt").write_text(stamp,"ascii")
    print(stamp,end="")
    return stamp


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",type=Path,required=True)
    opt=p.parse_args()
    try:
        audit(opt.evidence)
    except (OSError,UnicodeError,ValueError) as error:
        opt.evidence.mkdir(parents=True,exist_ok=True)
        (opt.evidence/"guard-cooldown-refill-x11-result.txt").write_text(
            "INCONCLUSIVE: "+str(error)+"\n","ascii")
        p.exit(1,"NeXium real guard cooldown refill unverified: "+str(error)+"\n")
