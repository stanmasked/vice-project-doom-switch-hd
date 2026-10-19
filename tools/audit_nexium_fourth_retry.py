#!/usr/bin/env python3
"""Fail-closed fourth manual replay after a third genuine earned victory."""
import argparse
import hashlib
from pathlib import Path
import re

PREFIX="VPD_ROMFREE_FOURTH_RETRY_V1"
RESTART=("seq","event","old_frame","old_hp","old_guard_hp",
         "old_sentry_hp","old_clear","new_frame","new_x",
         "hero_hp","guard_hp","sentry_hp","wave","clear","input_minus",
         "source","original_game_proven")
MOVE=("seq","event","frame","before_frame","before_x","after_x",
      "delta_fixed","hero_hp","guard_hp","sentry_hp","guard_attacks",
      "shots","wave","clear","input_right","source","original_game_proven")
HEADER=re.compile(rb"\AP6\n(?:\#[ -~]{1,200}\n){0,3}1280 720\n255\n")
SPAWN=3*16*256

def parsed(line,keys,seq,event):
    cells=line.split(" ")
    if not cells or cells[0]!=PREFIX or len(cells)!=len(keys)+1:
        raise ValueError("invalid fourth replay source witness shape")
    pairs=[x.split("=",1) for x in cells[1:]]
    if any(len(p)!=2 for p in pairs) or tuple(p[0] for p in pairs)!=keys:
        raise ValueError("fourth replay source witness field order invalid")
    row=dict(pairs)
    if (row["seq"]!=str(seq) or row["event"]!=event or
        row["source"]!="live_guest" or
        row["original_game_proven"]!="no"):
        raise ValueError("forged fourth replay source or event")
    values={}
    for key in keys:
        if key in ("seq","event","source","original_game_proven"):
            continue
        if not re.fullmatch(r"0|[1-9][0-9]*",row[key]):
            raise ValueError("noncanonical numeric fourth replay field "+key)
        values[key]=int(row[key])
    return values

def verify(raw):
    if not isinstance(raw,bytes) or not raw or len(raw)>1000:
        raise ValueError("native fourth replay guest trace absent/oversized")
    value=raw.decode("ascii")
    if not value.endswith("\n") or "\r" in value or "\x00" in value:
        raise ValueError("invalid source witness line terminators")
    rows=value.splitlines()
    if len(rows)!=2:
        raise ValueError("fourth replay requires exactly two guest events")
    rst=parsed(rows[0],RESTART,1,"restart")
    move=parsed(rows[1],MOVE,2,"move")
    if (not 1<=rst["old_frame"]<=1200 or
        not 1<=rst["old_hp"]<=5 or rst["old_guard_hp"]!=0 or
        rst["old_sentry_hp"]!=0 or rst["old_clear"]!=1 or
        rst["new_frame"]!=0 or rst["new_x"]!=SPAWN or
        rst["hero_hp"]!=5 or rst["guard_hp"]!=3 or
        rst["sentry_hp"]!=2 or
        any(rst[x]!=0 for x in ("wave","clear")) or
        rst["input_minus"]!=1):
        raise ValueError("fourth retry not earned by a prior source victory")
    if (not 8<=move["frame"]<=100 or
        move["before_frame"]+1!=move["frame"] or
        not SPAWN<=move["before_x"] or
        move["after_x"]-move["before_x"]!=2*256 or
        move["delta_fixed"]!=2*256 or
        not SPAWN+16*256<=move["after_x"]<=SPAWN+120*256 or
        move["hero_hp"]!=5 or move["guard_hp"]!=3 or
        move["sentry_hp"]!=2 or move["input_right"]!=1 or
        any(move[k]!=0 for k in ("guard_attacks","shots","wave","clear"))):
        raise ValueError("fourth attempt did not move a freshly reset hero")
    return {"old_frame":rst["old_frame"],"frame":move["frame"],
            "after_x":move["after_x"]}

def raster(base,key):
    png=base/(key+".png")
    ppm=base/(key+".ppm")
    if not png.is_file() or not png.read_bytes().startswith(
            b"\x89PNG\r\n\x1a\n"):
        raise ValueError("missing original X11 fourth-run PNG: "+key)
    if not ppm.is_file():
        raise ValueError("missing native fourth-run P6 image: "+key)
    raw=ppm.read_bytes()
    match=HEADER.match(raw)
    if not match or len(raw)!=match.end()+3*1280*720:
        raise ValueError("invalid fourth-run native 1280x720 X11 image")
    return raw[match.end():],hashlib.sha256(raw).hexdigest()

def audit(evidence):
    base=Path(evidence)
    src=base/"guest-fourth-retry-witness.txt"
    if not src.is_file():
        raise ValueError("fourth guest restart and control record missing")
    state=verify(src.read_bytes())
    third=base/"third-stage-result.txt"
    if not third.is_file() or not third.read_text(encoding="ascii").startswith(
            "VPD_NEXIUM_THIRD_STAGE_PASS "):
        raise ValueError("earlier real third-stage victory and X11 PASS absent")
    host=base/"input-probe.txt"
    if not host.is_file():
        raise ValueError("native fourth-run host key log absent")
    controls=host.read_text(encoding="ascii").splitlines()
    for mark in (
        "host_fourth_retry_minus_sent=yes key=N guest_restart=yes",
        "host_fourth_retry_right_sent=yes key=D guest_move=yes",
    ):
        if mark not in controls:
            raise ValueError("native fourth-run Minus/Right inputs unobserved")
    trace=base/"visual-probe.txt"
    if not trace.is_file():
        raise ValueError("real fourth-run X11 screenshots absent")
    stamps=trace.read_text(encoding="ascii").splitlines()
    for mark in (
        "capture=screen-live-fourth-restart",
        "capture=screen-live-fourth-move",
        "live_fourth_movement_raster_after_guest_event=yes",
    ):
        if mark not in stamps:
            raise ValueError("fourth-run X11 image not guest-event aligned")
    a,sha1=raster(base,"screen-live-fourth-restart")
    b,sha2=raster(base,"screen-live-fourth-move")
    # Same hero rectangle tested in the successful third-run control proof.
    changed=0
    for y in range(554,604):
        lo=(y*1280+75)*3
        hi=(y*1280+250)*3
        first=a[lo:hi]
        last=b[lo:hi]
        changed+=sum(first[i:i+3]!=last[i:i+3]
                     for i in range(0,len(first),3))
    if changed<200:
        raise ValueError("fourth restored hero did not visibly move")
    result=("VPD_NEXIUM_FOURTH_RETRY_PASS "
            f"old_third_clear_frame={state['old_frame']} "
            f"fourth_move_frame={state['frame']} "
            "hero_hp=5 guard_hp=3 sentry_hp=2 "
            "real_pad_minus=yes real_pad_right=yes source=live_guest "
            f"changed_actor_pixels={changed} "
            f"restart_ppm_sha256={sha1} move_ppm_sha256={sha2} "
            "native_x11_evidence=yes original_game_proven=no "
            "physical_switch_proven=no\n")
    (base/"fourth-retry-result.txt").write_text(result,encoding="ascii")
    print(result,end="")
    return state

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    args=parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError,UnicodeError,ValueError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"fourth-retry-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        parser.exit(1,"Live fourth manual restart unverified: "+str(exc)+"\n")
