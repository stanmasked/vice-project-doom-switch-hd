#!/usr/bin/env python3
"""Real fourth-run Fire + first guard swept-impact proof; fail closed."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/"tools"/path)
    value=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value
third=module("third_fire_combat","audit_nexium_third_run_fire.py")
fourth=module("fourth_run_control","audit_nexium_fourth_retry.py")
GUEST=b"VPD_ROMFREE_FOURTH_COMBAT_V1"
PREVIOUS=b"VPD_ROMFREE_THIRD_FIRE_V1"
P6=re.compile(rb"\AP6\n(?:\#[ -~]{1,200}\n){0,3}1280 720\n255\n")

def verify(raw):
    if not isinstance(raw,bytes) or not raw or len(raw)>950:
        raise ValueError("native fourth-run combat guest events missing/oversized")
    if raw.count(GUEST)!=2 or PREVIOUS in raw:
        raise ValueError("fourth-run combat must contain two new source events")
    # Strictly reuse the previously successful identical source physics
    # schema; only its fourth-attempt provenance marker differs.
    return third.verify(raw.replace(GUEST,PREVIOUS))

def raster(base,name):
    png=base/(name+".png")
    ppm=base/(name+".ppm")
    if not png.is_file() or not png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("missing genuine fourth-run X11 PNG "+name)
    if not ppm.is_file():
        raise ValueError("missing genuine fourth-run X11 P6 "+name)
    raw=ppm.read_bytes()
    h=P6.match(raw)
    if not h or len(raw)!=h.end()+1280*720*3:
        raise ValueError("fourth-run screenshot not native 8-bit 1280x720 P6")
    return raw[h.end():],hashlib.sha256(raw).hexdigest()

def audit(evidence):
    base=Path(evidence)
    guest=base/"guest-fourth-combat-witness.txt"
    if not guest.is_file():
        raise ValueError("real fourth-run combat guest witness absent")
    combat=verify(guest.read_bytes())
    replay=base/"guest-fourth-retry-witness.txt"
    if not replay.is_file():
        raise ValueError("fourth-run source restart and move evidence absent")
    movement=fourth.verify(replay.read_bytes())
    if (not movement["frame"]<combat["fire_frame"]<combat["hit_frame"] or
        not movement["after_x"]<=combat["hero_x"]<=
        movement["after_x"]+48*256):
        raise ValueError("fourth-run shot unrelated to native restored hero")
    prior=base/"fourth-retry-result.txt"
    if not prior.is_file() or not prior.read_text(encoding="ascii").startswith(
        "VPD_NEXIUM_FOURTH_RETRY_PASS "):
        raise ValueError("prior native fourth-run guest and X11 PASS absent")
    host=base/"input-probe.txt"
    if not host.is_file():
        raise ValueError("physical fourth-run Y/Fire host record absent")
    lines=host.read_text(encoding="ascii").splitlines()
    for mark in (
        "host_fourth_run_fire_sent=yes key=Z guest_fire=yes",
        "host_fourth_run_hit_observed=yes",
    ):
        if mark not in lines:
            raise ValueError("real pad fourth Fire/impact unobserved: "+mark)
    trace=base/"visual-probe.txt"
    if not trace.is_file():
        raise ValueError("fourth-run source-aligned image trace absent")
    marks=trace.read_text(encoding="ascii").splitlines()
    for mark in (
        "capture=screen-live-fourth-move",
        "capture=screen-live-fourth-impact",
        "live_fourth_impact_raster_after_guest_event=yes",
    ):
        if mark not in marks:
            raise ValueError("fourth-run native X11 capture unobserved: "+mark)
    old,hash_before=raster(base,"screen-live-fourth-move")
    new,hash_after=raster(base,"screen-live-fourth-impact")
    count=0
    for y in range(530,631):
        a=(y*1280+405)*3
        b=(y*1280+690)*3
        x=old[a:b]
        z=new[a:b]
        count+=sum(x[i:i+3]!=z[i:i+3] for i in range(0,len(x),3))
    if count<300:
        raise ValueError("no live X11 difference near struck fourth-run guard")
    result=(
        "VPD_NEXIUM_FOURTH_COMBAT_PASS "
        f"fire_frame={combat['fire_frame']} "
        f"hit_frame={combat['hit_frame']} "
        "shots=1 guard_hits=1 guard_hp_before=3 guard_hp_after=2 "
        "real_pad_fire=yes source=live_guest "
        f"changed_guard_pixels={count} "
        f"before_ppm_sha256={hash_before} after_ppm_sha256={hash_after} "
        "native_x11_evidence=yes original_game_proven=no "
        "physical_switch_proven=no\n")
    (base/"fourth-combat-result.txt").write_text(result,encoding="ascii")
    print(result,end="")
    return combat

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",type=Path,required=True)
    args=p.parse_args()
    try:
        audit(args.evidence)
    except (OSError,ValueError,UnicodeError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"fourth-combat-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        p.exit(1,"Fourth-run physical Fire and guard impact unverified: "+str(exc)+"\n")
