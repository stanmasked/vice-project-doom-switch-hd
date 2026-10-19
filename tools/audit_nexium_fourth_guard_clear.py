#!/usr/bin/env python3
"""Fail closed unless fourth live run actually defeats the restored guard."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
def load(module,path):
    spec=importlib.util.spec_from_file_location(module,ROOT/"tools"/path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result
prior_guard=load("third_guard_for_fourth",
                 "audit_nexium_third_guard_clear.py")
prior_fire=load("fourth_fire_for_guard",
                "audit_nexium_fourth_combat.py")
FOURTH=b"VPD_ROMFREE_FOURTH_GUARD_CLEAR_V1"
THIRD=b"VPD_ROMFREE_THIRD_GUARD_CLEAR_V1"
P6=re.compile(rb"\AP6\n(?:\#[ -~]{1,200}\n){0,3}1280 720\n255\n")

def verify(raw):
    if not isinstance(raw,bytes) or raw.count(FOURTH)!=1 or THIRD in raw:
        raise ValueError("fourth guard source event must occur exactly once")
    return prior_guard.verify(raw.replace(FOURTH,THIRD))

def raster(base,name):
    png=base/(name+".png")
    ppm=base/(name+".ppm")
    if not png.is_file() or not png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("native fourth guard X11 PNG missing: "+name)
    if not ppm.is_file():
        raise ValueError("native fourth guard X11 P6 missing: "+name)
    data=ppm.read_bytes()
    h=P6.match(data)
    if not h or len(data)!=h.end()+1280*720*3:
        raise ValueError("fourth guard X11 capture not raw 1280x720 P6")
    return data[h.end():],hashlib.sha256(data).hexdigest()

def audit(evidence):
    base=Path(evidence)
    source=base/"guest-fourth-guard-clear-witness.txt"
    if not source.is_file():
        raise ValueError("fourth live guard clear source event absent")
    clear=verify(source.read_bytes())
    original=base/"guest-fourth-combat-witness.txt"
    if not original.is_file():
        raise ValueError("first fourth-run Fire/impact source missing")
    first=prior_fire.verify(original.read_bytes())
    if (not first["hit_frame"]<clear["frame"]<=first["hit_frame"]+160 or
        clear["hero_x"]!=first["hero_x"]):
        raise ValueError("final fourth guard hit not linked to first impact")
    passfile=base/"fourth-combat-result.txt"
    if not passfile.is_file() or not passfile.read_text(encoding="ascii").startswith(
            "VPD_NEXIUM_FOURTH_COMBAT_PASS "):
        raise ValueError("native fourth Fire/impact X11 PASS absent")
    host=base/"input-probe.txt"
    if not host.is_file() or (
        "host_fourth_guard_clear_sent=yes key=Z observed=yes"
        not in host.read_text(encoding="ascii").splitlines()
    ):
        raise ValueError("fourth guard kill lacks real held X11 Fire")
    timeline=base/"visual-probe.txt"
    if not timeline.is_file():
        raise ValueError("fourth guard X11 event timeline absent")
    for mark in (
        "capture=screen-live-fourth-impact",
        "capture=screen-live-fourth-guard-clear",
        "live_fourth_guard_clear_raster_after_guest_event=yes",
    ):
        if mark not in timeline.read_text(encoding="ascii").splitlines():
            raise ValueError("fourth guard X11 capture not guest-event aligned")
    before,old_sha=raster(base,"screen-live-fourth-impact")
    after,new_sha=raster(base,"screen-live-fourth-guard-clear")
    changed=0
    for y in range(530,631):
        lo=(y*1280+405)*3
        hi=(y*1280+690)*3
        lhs=before[lo:hi]
        rhs=after[lo:hi]
        changed+=sum(lhs[i:i+3]!=rhs[i:i+3]
                     for i in range(0,len(lhs),3))
    if changed<300:
        raise ValueError("native fourth guard defeat has no visible X11 change")
    report=("VPD_NEXIUM_FOURTH_GUARD_CLEAR_PASS "
            f"frame={clear['frame']} shots_fired={clear['shots']} "
            "hero_hp=5 guard_hp_before=1 guard_hp_after=0 "
            "guard_hits_total=3 real_pad_fire=yes source=live_guest "
            f"changed_guard_pixels={changed} "
            f"before_ppm_sha256={old_sha} after_ppm_sha256={new_sha} "
            "native_x11_evidence=yes original_game_proven=no "
            "physical_switch_proven=no\n")
    (base/"fourth-guard-clear-result.txt").write_text(report,encoding="ascii")
    print(report,end="")
    return clear

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    args=parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError,UnicodeError,ValueError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"fourth-guard-clear-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        parser.exit(1,"Fourth source guard defeat not proven: "+str(exc)+"\n")
