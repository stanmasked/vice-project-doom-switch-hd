#!/usr/bin/env python3
"""Audit real pad-driven third-run second-wave entry and earned exit."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "third_guard",ROOT/"tools/audit_nexium_third_guard_clear.py")
guard=importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

PREFIX="VPD_ROMFREE_THIRD_STAGE_V1"
KEYS=("seq","event","frame","hero_x","hero_hp","guard_hp",
      "guard_hits","sentry_hp","sentry_hits","wave","clear",
      "input_right","input_fire","source","original_game_proven")
NUMS=("frame","hero_x","hero_hp","guard_hp","guard_hits",
      "sentry_hp","sentry_hits","wave","clear","input_right","input_fire")
P6=re.compile(rb"\AP6\n(?:\#[ -~]{1,200}\n){0,3}1280 720\n255\n")

def verify(raw):
    if not isinstance(raw,bytes) or not raw or len(raw)>950:
        raise ValueError("missing/oversized third-run native stage witness")
    source=raw.decode("ascii")
    if not source.endswith("\n") or "\r" in source or "\x00" in source:
        raise ValueError("third stage witness must have canonical LF lines")
    lines=source.splitlines()
    if len(lines)!=2:
        raise ValueError("third stage requires exactly two native events")
    rows=[]
    for seq,(ev,line) in enumerate(zip(("wave","exit"),lines),1):
        cols=line.split(" ")
        if cols[0]!=PREFIX or len(cols)!=len(KEYS)+1:
            raise ValueError("malformed third stage guest record")
        pairs=[col.split("=",1) for col in cols[1:]]
        if any(len(p)!=2 for p in pairs) or tuple(p[0] for p in pairs)!=KEYS:
            raise ValueError("unexpected third stage witness field ordering")
        v=dict(pairs)
        if (v["seq"]!=str(seq) or v["event"]!=ev or
            v["source"]!="live_guest" or
            v["original_game_proven"]!="no"):
            raise ValueError("third stage guest event source or order forged")
        for key in NUMS:
            if not re.fullmatch(r"0|[1-9][0-9]*",v[key]):
                raise ValueError("noncanonical third stage numeric field")
        nums={key:int(v[key]) for key in NUMS}
        if (not 1<=nums["frame"]<=1200 or
            not 1<=nums["hero_hp"]<=5 or nums["guard_hp"]!=0 or
            nums["guard_hits"]!=3 or nums["wave"]!=1 or
            nums["input_right"]!=1 or nums["input_fire"] not in (0,1)):
            raise ValueError("source guard/wave/movement progression invalid")
        rows.append(nums)
    first,last=rows
    if (first["hero_x"]<26*16*256 or first["clear"]!=0 or
        first["sentry_hp"]!=2 or first["sentry_hits"]!=0):
        raise ValueError("third guard kill did not genuinely open second wave")
    if (not first["frame"]<last["frame"] or
        first["hero_x"]>=last["hero_x"] or
        last["hero_x"]<55*16*256 or
        last["clear"]!=1 or last["sentry_hp"]!=0 or
        last["sentry_hits"]!=2 or last["input_fire"]!=1):
        raise ValueError("third stage failed to defeat sentry and earn exit")
    return {"wave_frame":first["frame"],"exit_frame":last["frame"],
            "exit_x":last["hero_x"]}

def raster(base,name):
    png=base/(name+".png")
    ppm=base/(name+".ppm")
    if not png.is_file() or not png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("real third-stage X11 PNG missing: "+name)
    if not ppm.is_file():
        raise ValueError("real third-stage X11 P6 missing: "+name)
    data=ppm.read_bytes()
    header=P6.match(data)
    if not header or len(data)!=header.end()+1280*720*3:
        raise ValueError("third-stage native X11 image is not 1280x720 raw P6")
    return data[header.end():],hashlib.sha256(data).hexdigest()

def audit(evidence):
    base=Path(evidence)
    path=base/"guest-third-stage-witness.txt"
    if not path.is_file():
        raise ValueError("third-stage real guest SD witness missing")
    values=verify(path.read_bytes())
    previous=base/"guest-third-guard-clear-witness.txt"
    if not previous.is_file():
        raise ValueError("third-stage prior genuine guard defeat absent")
    initial=guard.verify(previous.read_bytes())
    if initial["frame"]>=values["wave_frame"]:
        raise ValueError("third-stage wave occurred before its guard kill")
    result=base/"third-guard-clear-result.txt"
    if not result.is_file() or not result.read_text(encoding="ascii").startswith(
        "VPD_NEXIUM_THIRD_GUARD_CLEAR_PASS "):
        raise ValueError("prior native third-run X11 guard-clear PASS missing")
    host=base/"input-probe.txt"
    if not host.is_file():
        raise ValueError("missing real host third-stage controller log")
    lines=host.read_text(encoding="ascii").splitlines()
    for required in (
        "host_third_stage_gate_sent=yes key=D observed=yes",
        "host_third_stage_exit_sent=yes keys=D+Z observed=yes",
    ):
        if required not in lines:
            raise ValueError("real third-stage Right/Fire controller chain missing")
    trace=base/"visual-probe.txt"
    if not trace.is_file():
        raise ValueError("third-stage X11 capture timeline absent")
    seen=trace.read_text(encoding="ascii").splitlines()
    for mark in (
        "capture=screen-live-third-guard-clear",
        "capture=screen-live-third-stage-clear",
        "live_third_stage_clear_raster_after_guest_event=yes",
    ):
        if mark not in seen:
            raise ValueError("third stage exit X11 raster not event aligned")
    before,before_hash=raster(base,"screen-live-third-guard-clear")
    after,after_hash=raster(base,"screen-live-third-stage-clear")
    changed=0
    for y in range(230,395):
        p=(y*1280+355)*3
        q=(y*1280+925)*3
        lhs=before[p:q]
        rhs=after[p:q]
        changed+=sum(lhs[i:i+3]!=rhs[i:i+3] for i in range(0,len(lhs),3))
    if changed<500:
        raise ValueError("third-run stage clear did not visibly update scene")
    summary=(
        "VPD_NEXIUM_THIRD_STAGE_PASS "
        f"wave_frame={values['wave_frame']} exit_frame={values['exit_frame']} "
        "hero_alive=yes guard_dead=yes sentry_hits=2 "
        "stage_clear=yes real_pad_right_fire=yes source=live_guest "
        f"changed_center_pixels={changed} "
        f"before_ppm_sha256={before_hash} after_ppm_sha256={after_hash} "
        "native_x11_evidence=yes original_game_proven=no "
        "physical_switch_proven=no\n")
    (base/"third-stage-result.txt").write_text(summary,encoding="ascii")
    print(summary,end="")
    return values

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    args=parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError,UnicodeError,ValueError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"third-stage-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        parser.exit(1,"Third-run live second stage unverified: "+str(exc)+"\n")
