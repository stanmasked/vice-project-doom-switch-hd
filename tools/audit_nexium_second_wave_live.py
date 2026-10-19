#!/usr/bin/env python3
"""Fail-closed verification of real pad-driven second-wave completion in NRO.

Unlike the independent guest-scripted wave test, this witness is emitted by
the same visible manually controlled Simulation after first-guard defeat.
"""
import argparse
from pathlib import Path
import re

PREFIX="VPD_ROMFREE_WAVE2_LIVE_V1"
EVENTS=("wave","fire","hit1","defeat","exit")
FIELDS=("seq","event","frame","player_x","hero_hp","turret_hp",
        "turret_hits","turret_shots","hero_shots","wave","clear",
        "input_right","input_fire","source","original_game_proven")
NUMS=("frame","player_x","hero_hp","turret_hp","turret_hits",
      "turret_shots","hero_shots","wave","clear",
      "input_right","input_fire")
MAP_LIMIT=64*16*256
EXIT_X=55*16*256
WAVE_X=26*16*256

def verify(raw):
    if not isinstance(raw,bytes) or not raw or len(raw)>2100:
        raise ValueError("native live stage-two log absent or oversized")
    text=raw.decode("ascii")
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise ValueError("malformed native live stage-two record terminator")
    lines=text.splitlines()
    if len(lines)!=5:
        raise ValueError("must observe five genuine live stage-two events")
    rows=[]
    for i,(event,line) in enumerate(zip(EVENTS,lines),1):
        columns=line.split(" ")
        if columns[0]!=PREFIX or len(columns)!=len(FIELDS)+1:
            raise ValueError("invalid live stage-two record shape")
        pairs=[c.split("=",1) for c in columns[1:]]
        if any(len(p)!=2 for p in pairs) or tuple(p[0] for p in pairs)!=FIELDS:
            raise ValueError("noncanonical live stage-two field order")
        row=dict(pairs)
        if (row["seq"]!=str(i) or row["event"]!=event or
            row["source"]!="live_guest" or
            row["original_game_proven"]!="no"):
            raise ValueError("live pad evidence source/order invalid")
        for key in NUMS:
            if not re.fullmatch(r"0|[1-9][0-9]*",row[key]):
                raise ValueError("noncanonical numeric live stage field")
        num={key:int(row[key]) for key in NUMS}
        if not (1<=num["frame"]<=1400 and 0<=num["player_x"]<=MAP_LIMIT and
                1<=num["hero_hp"]<=5 and 0<=num["turret_hp"]<=2 and
                0<=num["turret_hits"]<=2 and
                0<=num["turret_shots"]<=50 and
                1<=num["hero_shots"]<=100 and
                num["wave"]==1 and num["clear"] in (0,1) and
                num["input_right"] in (0,1) and
                num["input_fire"] in (0,1)):
            raise ValueError("impossible wave-two world or control state")
        if num["turret_hp"]+num["turret_hits"]!=2:
            raise ValueError("native turret health is inconsistent with hits")
        rows.append(num)
    wave,fire,hit,dead,exit_state=rows
    if wave["player_x"]<WAVE_X or wave["turret_hp"]!=2 or wave["clear"] or not wave["input_right"]:
        raise ValueError("actual live wave gate not confirmed")
    if (fire["turret_hp"]!=2 or fire["turret_hits"]!=0 or fire["clear"] or
        not fire["input_right"] or not fire["input_fire"] or
        fire["hero_shots"]<wave["hero_shots"] or
        fire["frame"]<wave["frame"]):
        raise ValueError("real Right+Fire did not launch a wave-two shot")
    if (hit["turret_hp"]!=1 or hit["turret_hits"]!=1 or hit["clear"] or
        hit["frame"]<=fire["frame"]):
        raise ValueError("first native turret projectile impact absent")
    if (dead["turret_hp"]!=0 or dead["turret_hits"]!=2 or dead["clear"] or
        dead["frame"]<=hit["frame"]):
        raise ValueError("second impact failed to destroy turret")
    if (not exit_state["clear"] or exit_state["player_x"]<EXIT_X or
        exit_state["turret_hp"]!=0 or exit_state["turret_hits"]!=2 or
        exit_state["frame"]<=dead["frame"]):
        raise ValueError("no real guest-controller stage exit reached")
    for previous,current in zip(rows,rows[1:]):
        if current["hero_shots"]<previous["hero_shots"] or (
            current["frame"]<previous["frame"]
        ):
            raise ValueError("live source shots/frames are nonmonotonic")
    return {"wave_frame":wave["frame"],"fire_frame":fire["frame"],
            "hit_frame":hit["frame"],"defeat_frame":dead["frame"],
            "exit_frame":exit_state["frame"]}

def audit(folder):
    base=Path(folder)
    path=base/"guest-second-wave-live-witness.txt"
    if not path.is_file():
        raise ValueError("NeXium guest omitted real pad-controlled wave-two log")
    observed=verify(path.read_bytes())
    host=base/"input-probe.txt"
    if not host.is_file() or (
        "host_second_wave_controls_sent=yes keys=D+Z guest_exit=yes"
        not in host.read_text(encoding="ascii").splitlines()
    ):
        raise ValueError("host did not confirm sending separate Right+Fire stage controls")
    for name,marker in (
        ("manual-result.txt","VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "),
        ("dash-result.txt","VPD_NEXIUM_GUEST_DASH_PASS "),
        ("guard-live-result.txt","VPD_NEXIUM_GUARD_LIVE_CONTACT_PASS "),
        ("guard-live-defeat-result.txt","VPD_NEXIUM_GUARD_LIVE_DEFEAT_PASS "),
        ("guard-live-raster-result.txt","VPD_NEXIUM_GUARD_LIVE_RASTER_PASS "),
        ("second-wave-result.txt","VPD_NEXIUM_SECOND_WAVE_SCRIPT_PASS "),
        ("native-exit-result.txt","VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
    ):
        check=base/name
        if not check.is_file() or not check.read_text(encoding="ascii").startswith(marker):
            raise ValueError("independent native stage prerequisite missing: "+name)
    first=(base/"guest-guard-live-defeat-witness.txt")
    if not first.is_file():
        raise ValueError("independent live first-guard kill trace missing")
    lines=first.read_text(encoding="ascii").splitlines()
    if not lines or " event=defeat " not in lines[-1]:
        raise ValueError("native first-guard kill never observed")
    m=re.search(r"\bframe=([1-9][0-9]*)\b",lines[-1])
    if not m or observed["wave_frame"]<=int(m.group(1)):
        raise ValueError("second wave not triggered after first guard death")
    png=base/"screen-live-stage-clear.png"
    if not png.is_file() or not png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("native live stage-clear X11 screenshot missing")
    trace=base/"visual-probe.txt"
    if not trace.is_file() or (
        "live_second_wave_exit_raster_after_guest_event=yes"
        not in trace.read_text(encoding="ascii").splitlines()
    ):
        raise ValueError("native stage-clear screenshot not tied to guest exit")
    result=(
        "VPD_NEXIUM_SECOND_WAVE_LIVE_PASS "
        f"wave_frame={observed['wave_frame']} "
        f"fire_frame={observed['fire_frame']} "
        f"hit_frame={observed['hit_frame']} "
        f"turret_defeat_frame={observed['defeat_frame']} "
        f"exit_frame={observed['exit_frame']} "
        "input=real_pad_right_fire turret_hits=2 stage_clear=yes "
        "visible_manual_simulation=yes physical_switch_proven=no "
        "original_game_proven=no\n"
    )
    (base/"second-wave-live-result.txt").write_text(result,encoding="ascii")
    print(result,end="")
    return observed

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    args=parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError,UnicodeError,ValueError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"second-wave-live-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        parser.exit(1,"Live manual second-wave gameplay unverified: "+str(exc)+"\n")
