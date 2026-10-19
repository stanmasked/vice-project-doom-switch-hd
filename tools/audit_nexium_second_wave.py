#!/usr/bin/env python3
"""Audit actual native NRO execution of separate ROM-free stage-two scripts.

These are bounded *guest-executed* simulations, NOT live controller-driven
second-wave play or evidence of original NES behavior.
"""
import argparse
from pathlib import Path
import re

MARK="VPD_ROMFREE_WAVE2_V1"
EVENTS=("guard","wave","hostile_hit","turret_down","exit")
FIELDS=("seq","event","scenario","frame","player_x","guard_hp",
        "sentry_hp","player_hp","sentry_shots","sentry_hits",
        "sentry_damage","wave","clear","source","original_game_proven")
NUMBERS=("frame","player_x","guard_hp","sentry_hp","player_hp",
         "sentry_shots","sentry_hits","sentry_damage","wave","clear")
EXIT=55*16*256


def verify(raw):
    if not isinstance(raw,bytes) or not raw or len(raw)>2200:
        raise ValueError("native second-wave witness missing or oversized")
    t=raw.decode("ascii")
    if not t.endswith("\n") or "\r" in t or "\x00" in t:
        raise ValueError("invalid guest second-wave text termination")
    lines=t.splitlines()
    if len(lines)!=5:
        raise ValueError("five source-complete stage-two events required")
    rows=[]
    for idx,(event,line) in enumerate(zip(EVENTS,lines),1):
        cols=line.split(" ")
        if len(cols)!=len(FIELDS)+1 or cols[0]!=MARK:
            raise ValueError("incorrect second-wave record marker/size")
        pairs=[c.split("=",1) for c in cols[1:]]
        if any(len(p)!=2 for p in pairs) or (
            tuple(p[0] for p in pairs)!=FIELDS
        ):
            raise ValueError("incorrect second-wave field order")
        row=dict(pairs)
        scenario="stationary" if idx==3 else "stage"
        if (row["seq"]!=str(idx) or row["event"]!=event or
            row["scenario"]!=scenario or
            row["source"]!="guest_script" or
            row["original_game_proven"]!="no"):
            raise ValueError("wrong second-wave event provenance")
        for key in NUMBERS:
            if not re.fullmatch(r"0|[1-9][0-9]*",row[key]):
                raise ValueError("noncanonical second-wave numeric field")
        data={key:int(row[key]) for key in NUMBERS}
        if (not 1<=data["frame"]<=1200 or
            not 0<=data["player_x"]<=64*16*256 or
            not 0<=data["guard_hp"]<=3 or
            not 0<=data["sentry_hp"]<=2 or
            not 0<=data["player_hp"]<=5 or
            data["sentry_shots"]>100 or data["sentry_hits"]>10 or
            data["sentry_damage"]>2 or
            data["wave"] not in (0,1) or data["clear"] not in (0,1)):
            raise ValueError("impossible stage-two guest state")
        rows.append(data)
    guard,wave,hostile,defeat,exit_state=rows
    if not all(row["guard_hp"]==0 for row in rows):
        raise ValueError("stage-two data bypassed original guard gate")
    if (guard["wave"]!=0 or guard["clear"]!=0 or
        guard["sentry_hp"]!=2 or guard["player_hp"]!=5 or
        guard["sentry_shots"]!=0 or guard["sentry_damage"]!=0):
        raise ValueError("guard-gated section starts in wrong state")
    if (wave["wave"]!=1 or wave["clear"]!=0 or
        wave["sentry_hp"]!=2 or wave["sentry_shots"]!=0 or
        wave["player_x"]<26*16*256 or
        wave["frame"]<=guard["frame"]):
        raise ValueError("native guest failed to activate later section")
    if (hostile["wave"]!=1 or hostile["clear"]!=0 or
        hostile["sentry_hp"]!=2 or hostile["sentry_shots"]<1 or
        hostile["sentry_hits"]<1 or hostile["player_hp"]>=5 or
        hostile["sentry_damage"]!=0):
        raise ValueError("hostile sentry projectile damage not observed")
    if (defeat["wave"]!=1 or defeat["clear"]!=0 or
        defeat["sentry_hp"]!=0 or defeat["sentry_damage"]!=2 or
        defeat["player_hp"]<=0 or defeat["frame"]<=wave["frame"]):
        raise ValueError("two legitimate player hits did not disable turret")
    if (exit_state["wave"]!=1 or exit_state["clear"]!=1 or
        exit_state["sentry_hp"]!=0 or exit_state["sentry_damage"]!=2 or
        exit_state["player_hp"]<=0 or exit_state["player_x"]<EXIT or
        exit_state["frame"]<=defeat["frame"]):
        raise ValueError("living hero did not reach gated exit")
    return {"spawn_frame":wave["frame"],
            "hostile_hit_frame":hostile["frame"],
            "turret_defeat_frame":defeat["frame"],
            "exit_frame":exit_state["frame"]}


def audit(folder):
    root=Path(folder)
    witness=root/"guest-second-wave-witness.txt"
    if not witness.is_file():
        raise ValueError("native guest did not emit wave-two stage trace")
    values=verify(witness.read_bytes())
    for filename,marker in (
        ("manual-result.txt","VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "),
        ("dash-result.txt","VPD_NEXIUM_GUEST_DASH_PASS "),
        ("guard-result.txt","VPD_NEXIUM_GUARD_PATROL_PASS "),
        ("guard-live-defeat-result.txt","VPD_NEXIUM_GUARD_LIVE_DEFEAT_PASS "),
        ("guard-live-raster-result.txt","VPD_NEXIUM_GUARD_LIVE_RASTER_PASS "),
        ("native-exit-result.txt","VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
    ):
        path=root/filename
        if not path.is_file() or not path.read_text(
            encoding="ascii").startswith(marker):
            raise ValueError("independent native run proof missing: "+filename)
    line=(
        "VPD_NEXIUM_SECOND_WAVE_SCRIPT_PASS "
        f"spawn_frame={values['spawn_frame']} "
        f"hostile_hit_frame={values['hostile_hit_frame']} "
        f"turret_defeat_frame={values['turret_defeat_frame']} "
        f"exit_frame={values['exit_frame']} "
        "guard_gate=yes sentry_hostile_hit=yes turret_hits=2 "
        "level_exit=yes guest_sd_witness=yes "
        "live_manual_wave_proven=no original_game_proven=no\n"
    )
    (root/"second-wave-result.txt").write_text(line,encoding="ascii")
    print(line,end="")
    return values


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--evidence",type=Path,required=True)
    args=ap.parse_args()
    try:
        audit(args.evidence)
    except (OSError,ValueError,UnicodeError) as err:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"second-wave-result.txt").write_text(
            "INCONCLUSIVE: "+str(err)+"\n",encoding="ascii")
        ap.exit(1,"Second-wave native guest unverified: "+str(err)+"\n")
