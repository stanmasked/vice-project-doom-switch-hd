#!/usr/bin/env python3
"""Fail-closed third-attempt live Fire + swept guard projectile impact audit."""
import argparse
import hashlib
from pathlib import Path
import re
import importlib.util

PREFIX="VPD_ROMFREE_THIRD_FIRE_V1"
KEYS=("seq","event","frame","hero_x","hero_hp","guard_hp","guard_hits",
      "guard_attacks","shots","sentry_hp","wave","clear","dash",
      "input_fire","source","original_game_proven")
NUMS=("frame","hero_x","hero_hp","guard_hp","guard_hits",
      "guard_attacks","shots","sentry_hp","wave","clear","dash","input_fire")
HEADER=re.compile(rb"\AP6\n(?:\#[ -~]{1,200}\n){0,3}1280 720\n255\n")
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "third_run_core",ROOT/"tools/audit_nexium_third_run_control.py")
third=importlib.util.module_from_spec(spec)
spec.loader.exec_module(third)

def verify(raw):
    if not isinstance(raw,bytes) or not raw or len(raw)>1000:
        raise ValueError("native third-run Fire/impact witness missing or oversized")
    text=raw.decode("ascii")
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise ValueError("third-run combat source witness has invalid line endings")
    lines=text.splitlines()
    if len(lines)!=2:
        raise ValueError("exactly two ordered third-run source events required")
    rows=[]
    for seq,(event,line) in enumerate(zip(("fire","impact"),lines),1):
        columns=line.split(" ")
        if columns[0]!=PREFIX or len(columns)!=len(KEYS)+1:
            raise ValueError("invalid third-run combat witness shape")
        pair=[field.split("=",1) for field in columns[1:]]
        if any(len(p)!=2 for p in pair) or tuple(p[0] for p in pair)!=KEYS:
            raise ValueError("noncanonical third-run combat witness key order")
        row=dict(pair)
        if (row["seq"]!=str(seq) or row["event"]!=event or
            row["source"]!="live_guest" or
            row["original_game_proven"]!="no"):
            raise ValueError("third-run Fire/impact provenance or sequence forged")
        for key in NUMS:
            if not re.fullmatch(r"0|[1-9][0-9]*",row[key]):
                raise ValueError("noncanonical numeric combat state")
        v={key:int(row[key]) for key in NUMS}
        if (not 1<=v["frame"]<=240 or
            not (3*16+16)*256<=v["hero_x"]<=(3*16+80)*256 or
            v["hero_hp"]!=5 or v["guard_attacks"]!=0 or v["shots"]!=1 or
            v["sentry_hp"]!=2 or
            any(v[k]!=0 for k in ("wave","clear","dash")) or
            v["input_fire"] not in (0,1)):
            raise ValueError("third-run attack occurred outside fresh live arena")
        rows.append(v)
    fire,hit=rows
    if (fire["guard_hp"]!=3 or fire["guard_hits"]!=0 or
        fire["input_fire"]!=1 or hit["guard_hp"]!=2 or
        hit["guard_hits"]!=1 or hit["input_fire"]!=0 or
        not fire["frame"]<hit["frame"]<fire["frame"]+90 or
        fire["hero_x"]!=hit["hero_x"]):
        raise ValueError("shot creation and 1-HP swept guard hit mismatch")
    return {"fire_frame":fire["frame"],"hit_frame":hit["frame"],
            "hero_x":hit["hero_x"]}

def raster(base,key):
    png=base/(key+".png")
    ppm=base/(key+".ppm")
    if not png.is_file() or not png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("actual third-run PNG missing: "+key)
    if not ppm.is_file():
        raise ValueError("actual third-run P6 missing: "+key)
    raw=ppm.read_bytes()
    h=HEADER.match(raw)
    if not h or len(raw)!=h.end()+3*1280*720:
        raise ValueError("X11 third-run screenshot is not raw 1280x720 P6")
    return raw[h.end():],hashlib.sha256(raw).hexdigest()

def audit(evidence):
    base=Path(evidence)
    source=base/"guest-post-defeat-fire-witness.txt"
    if not source.is_file():
        raise ValueError("real third-run Fire guest SD witness missing")
    values=verify(source.read_bytes())
    proof=base/"guest-post-defeat-control-witness.txt"
    if not proof.is_file():
        raise ValueError("preceding third-run live movement witness absent")
    third_state=third.verify(proof.read_bytes())
    if not (third_state["frame"]<values["fire_frame"] and
            third_state["after_x"]<=values["hero_x"]<=
            third_state["after_x"]+48*256):
        raise ValueError("third-run Fire not linked to prior source movement")
    prior=base/"third-run-control-result.txt"
    if not prior.is_file() or not prior.read_text(encoding="ascii").startswith(
            "VPD_NEXIUM_THIRD_RUN_CONTROL_PASS "):
        raise ValueError("native third-run source and X11 control proof missing")
    host=base/"input-probe.txt"
    if not host.is_file():
        raise ValueError("host X11 Fire key evidence missing")
    host_lines=host.read_text(encoding="ascii").splitlines()
    for item in ("host_third_run_control_sent=yes key=D guest_observed=yes",
                 "host_third_run_fire_sent=yes key=Z guest_fire=yes",
                 "host_third_run_hit_observed=yes"):
        if item not in host_lines:
            raise ValueError("actual post-retry X11 Fire and impact absent: "+item)
    trace=base/"visual-probe.txt"
    if not trace.is_file():
        raise ValueError("native X11 third-run impact timeline absent")
    for item in ("capture=screen-live-third-run-move",
                 "capture=screen-live-third-run-impact",
                 "live_third_run_impact_raster_after_guest_event=yes"):
        if item not in trace.read_text(encoding="ascii").splitlines():
            raise ValueError("X11 guard-impact frame not event-aligned: "+item)
    before,digest1=raster(base,"screen-live-third-run-move")
    after,digest2=raster(base,"screen-live-third-run-impact")
    # The source guard patrols in world x=224..320, displayed x=448..640.
    # Restrict visual difference to the enemy's own on-screen region.
    changed=0
    for y in range(530,631):
        start=(y*1280+405)*3
        stop=(y*1280+690)*3
        a=before[start:stop]
        b=after[start:stop]
        changed+=sum(a[i:i+3]!=b[i:i+3] for i in range(0,len(a),3))
    if changed<300:
        raise ValueError("source guard impact has no corroborating X11 pixels")
    result=(
        "VPD_NEXIUM_THIRD_RUN_FIRE_PASS "
        f"fire_frame={values['fire_frame']} hit_frame={values['hit_frame']} "
        "shots=1 native_guard_hits=1 guard_hp_before=3 guard_hp_after=2 "
        "real_pad_fire=yes source=live_guest "
        f"changed_guard_region_pixels={changed} "
        f"before_ppm_sha256={digest1} after_ppm_sha256={digest2} "
        "native_x11_evidence=yes original_game_proven=no "
        "physical_switch_proven=no\n")
    (base/"third-run-fire-result.txt").write_text(result,encoding="ascii")
    print(result,end="")
    return values

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    args=parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError,UnicodeError,ValueError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"third-run-fire-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        parser.exit(1,"Real third-run Fire/impact unverified: "+str(exc)+"\n")
