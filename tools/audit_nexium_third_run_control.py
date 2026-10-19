#!/usr/bin/env python3
"""Strict check of actual post-defeat gameplay control in the same native NRO.

A real NeXium X11 Right keystroke, source-side one-tick player displacement,
and two original X11 frames are mandatory. Fixture validation is not proof.
"""
import argparse
import hashlib
from pathlib import Path
import re

PREFIX="VPD_ROMFREE_THIRD_RUN_V1"
KEYS=("event","frame","before_frame","before_x","after_x","delta_fixed",
      "hero_hp","guard_hp","guard_attacks","sentry_hp","shots","dash",
      "wave","clear","input_right","source","original_game_proven")
NUMS=("frame","before_frame","before_x","after_x","delta_fixed",
      "hero_hp","guard_hp","guard_attacks","sentry_hp","shots","dash",
      "wave","clear","input_right")
P6HEADER=re.compile(rb"\AP6\n(?:\#[ -~]{1,200}\n){0,3}1280 720\n255\n")
SPAWN=3*16*256
STEP=2*256

def verify(raw):
    if not isinstance(raw,bytes) or not raw or len(raw)>500:
        raise ValueError("third-run live guest evidence absent or oversized")
    data=raw.decode("ascii")
    if not data.endswith("\n") or "\r" in data or "\x00" in data or data.count("\n")!=1:
        raise ValueError("third-run source witness is not one canonical line")
    cols=data[:-1].split(" ")
    if not cols or cols[0]!=PREFIX or len(cols)!=len(KEYS)+1:
        raise ValueError("invalid third-run guest witness prefix/shape")
    pairs=[col.split("=",1) for col in cols[1:]]
    if any(len(p)!=2 for p in pairs) or tuple(p[0] for p in pairs)!=KEYS:
        raise ValueError("noncanonical third-run witness key sequence")
    values=dict(pairs)
    if (values["event"]!="move" or values["source"]!="live_guest" or
        values["original_game_proven"]!="no"):
        raise ValueError("third-run source and event provenance mismatch")
    for key in NUMS:
        if not re.fullmatch(r"0|[1-9][0-9]*",values[key]):
            raise ValueError("noncanonical third-run numeric value: "+key)
    v={key:int(values[key]) for key in NUMS}
    if (not 1<=v["frame"]<=100 or v["before_frame"]+1!=v["frame"] or
        not SPAWN<=v["before_x"] or
        not SPAWN+16*256<=v["after_x"]<=SPAWN+120*256 or
        v["after_x"]-v["before_x"]!=STEP or
        v["delta_fixed"]!=STEP or
        v["hero_hp"]!=5 or v["guard_hp"]!=3 or
        v["guard_attacks"]!=0 or v["sentry_hp"]!=2 or
        any(v[k]!=0 for k in ("shots","dash","wave","clear")) or
        v["input_right"]!=1):
        raise ValueError("third run did not move a healthy freshly reset hero")
    return {"frame":v["frame"],"after_x":v["after_x"],"delta":STEP}

def raster(directory,key):
    png=directory/(key+".png")
    ppm=directory/(key+".ppm")
    if not png.is_file() or not png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("native X11 PNG absent: "+key)
    if not ppm.is_file():
        raise ValueError("native X11 P6 framebuffer absent: "+key)
    raw=ppm.read_bytes()
    header=P6HEADER.match(raw)
    if not header or len(raw)!=header.end()+3*1280*720:
        raise ValueError("X11 framebuffer size or P6 encoding incorrect: "+key)
    return raw[header.end():],hashlib.sha256(raw).hexdigest()

def audit(evidence):
    base=Path(evidence)
    witness=base/"guest-post-defeat-control-witness.txt"
    if not witness.is_file():
        raise ValueError("native third-run guest SD witness absent")
    status=verify(witness.read_bytes())
    host=base/"input-probe.txt"
    if not host.is_file():
        raise ValueError("host third-run X11 controller evidence missing")
    host_lines=host.read_text(encoding="ascii").splitlines()
    for line in ("host_defeat_retry_guest_observed=yes",
                 "host_third_run_control_sent=yes key=D guest_observed=yes"):
        if line not in host_lines:
            raise ValueError("third-run actual Right/Minus chain incomplete")
    for file,prefix in (
        ("defeat-retry-result.txt","VPD_NEXIUM_DEFEAT_RETRY_PASS "),
        ("manual-retry-result.txt","VPD_NEXIUM_MANUAL_RETRY_PASS "),
        ("native-exit-result.txt","VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
    ):
        path=base/file
        if not path.is_file() or not path.read_text(encoding="ascii").startswith(prefix):
            raise ValueError("prior required native evidence missing: "+file)
    timeline=base/"visual-probe.txt"
    if not timeline.is_file():
        raise ValueError("third-run X11 capture timeline absent")
    events=timeline.read_text(encoding="ascii").splitlines()
    for label in (
        "capture=screen-live-defeat-restart",
        "capture=screen-live-third-run-move",
        "live_third_run_movement_raster_after_guest_event=yes",
    ):
        if label not in events:
            raise ValueError("third-run screenshot not tied to guest event: "+label)
    before,before_sha=raster(base,"screen-live-defeat-restart")
    after,after_sha=raster(base,"screen-live-third-run-move")
    # Native renderer maps the spawn x=48px -> 96 display pixels;
    # grounded hero at y=(210+80)*2=580. Inspect the ACTOR'S lower-left
    # stage region, excluding the constantly changing HUD.
    moved=0
    for y in range(554,604):
        left=(y*1280+75)*3
        right=(y*1280+250)*3
        previous=before[left:right]
        current=after[left:right]
        moved+=sum(previous[i:i+3]!=current[i:i+3]
                   for i in range(0,len(previous),3))
    if moved<200:
        raise ValueError("third-run actor region did not visibly update")
    result=("VPD_NEXIUM_THIRD_RUN_CONTROL_PASS "
            f"frame={status['frame']} actor_x_fixed={status['after_x']} "
            "per_tick_delta_fixed=512 actor_hp=5 guard_hp=3 "
            "real_host_right=yes source=live_guest "
            f"changed_actor_region_pixels={moved} "
            f"before_ppm_sha256={before_sha} after_ppm_sha256={after_sha} "
            "native_x11_evidence=yes original_game_proven=no "
            "physical_switch_proven=no\n")
    (base/"third-run-control-result.txt").write_text(result,encoding="ascii")
    print(result,end="")
    return status

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    args=parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError,UnicodeError,ValueError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"third-run-control-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        parser.exit(1,"Native third-playthrough control unverified: "+str(exc)+"\n")
