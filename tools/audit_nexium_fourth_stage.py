#!/usr/bin/env python3
"""Fourth genuine second-wave victory after three played terminal restarts."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/"tools"/path)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj
old_stage=load("prior_third_stage_fourth","audit_nexium_third_stage.py")
fourth_guard=load("fourth_guard_for_stage","audit_nexium_fourth_guard_clear.py")
NEW=b"VPD_ROMFREE_FOURTH_STAGE_V1"
OLD=b"VPD_ROMFREE_THIRD_STAGE_V1"
P6=re.compile(rb"\AP6\n(?:\#[ -~]{1,200}\n){0,3}1280 720\n255\n")

def verify(raw):
    if not isinstance(raw,bytes) or raw.count(NEW)!=2 or OLD in raw:
        raise ValueError("fourth stage needs two independently sourced events")
    return old_stage.verify(raw.replace(NEW,OLD))

def raster(base,name):
    p=base/(name+".png")
    q=base/(name+".ppm")
    if not p.is_file() or not p.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("fourth stage native X11 PNG not found: "+name)
    if not q.is_file():
        raise ValueError("fourth stage native X11 P6 not found: "+name)
    data=q.read_bytes()
    match=P6.match(data)
    if not match or len(data)!=match.end()+1280*720*3:
        raise ValueError("fourth stage screenshot invalid 1280x720 P6")
    return data[match.end():],hashlib.sha256(data).hexdigest()

def audit(evidence):
    base=Path(evidence)
    file=base/"guest-fourth-stage-witness.txt"
    if not file.is_file():
        raise ValueError("fourth stage live SD event pair absent")
    stage=verify(file.read_bytes())
    dead=base/"guest-fourth-guard-clear-witness.txt"
    if not dead.is_file():
        raise ValueError("fourth stage guard defeat source event absent")
    prior=fourth_guard.verify(dead.read_bytes())
    if not prior["frame"]<stage["wave_frame"]:
        raise ValueError("fourth wave fired before fourth guard kill")
    passfile=base/"fourth-guard-clear-result.txt"
    if not passfile.is_file() or not passfile.read_text(encoding="ascii").startswith(
        "VPD_NEXIUM_FOURTH_GUARD_CLEAR_PASS "):
        raise ValueError("fourth guard actual native X11 PASS missing")
    inputs=base/"input-probe.txt"
    if not inputs.is_file():
        raise ValueError("fourth stage X11 pad inputs not recorded")
    lines=inputs.read_text(encoding="ascii").splitlines()
    for must in (
        "host_fourth_stage_gate_sent=yes key=D observed=yes",
        "host_fourth_stage_exit_sent=yes keys=D+Z observed=yes",
    ):
        if must not in lines:
            raise ValueError("fourth stage real Right+Fire provenance missing")
    marker=base/"visual-probe.txt"
    if not marker.is_file():
        raise ValueError("fourth stage X11 capture timeline missing")
    stamps=marker.read_text(encoding="ascii").splitlines()
    for item in (
        "capture=screen-live-fourth-guard-clear",
        "capture=screen-live-fourth-stage-clear",
        "live_fourth_stage_clear_raster_after_guest_event=yes",
    ):
        if item not in stamps:
            raise ValueError("fourth stage screenshots not guest-event aligned")
    before,before_sha=raster(base,"screen-live-fourth-guard-clear")
    after,after_sha=raster(base,"screen-live-fourth-stage-clear")
    changes=0
    for y in range(230,395):
        a=(y*1280+355)*3
        b=(y*1280+925)*3
        x=before[a:b]
        z=after[a:b]
        changes+=sum(x[i:i+3]!=z[i:i+3] for i in range(0,len(x),3))
    if changes<500:
        raise ValueError("fourth stage completion produced no native screen change")
    output=(
        "VPD_NEXIUM_FOURTH_STAGE_PASS "
        f"wave_frame={stage['wave_frame']} exit_frame={stage['exit_frame']} "
        "hero_alive=yes guard_dead=yes sentry_hits=2 stage_clear=yes "
        "real_pad_right_fire=yes source=live_guest "
        f"changed_center_pixels={changes} "
        f"before_ppm_sha256={before_sha} after_ppm_sha256={after_sha} "
        "native_x11_evidence=yes original_game_proven=no "
        "physical_switch_proven=no\n")
    (base/"fourth-stage-result.txt").write_text(output,encoding="ascii")
    print(output,end="")
    return stage

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",type=Path,required=True)
    args=p.parse_args()
    try:
        audit(args.evidence)
    except (OSError,ValueError,UnicodeError) as e:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"fourth-stage-result.txt").write_text(
            "INCONCLUSIVE: "+str(e)+"\n",encoding="ascii")
        p.exit(1,"Fourth manual level completion unverified: "+str(e)+"\n")
