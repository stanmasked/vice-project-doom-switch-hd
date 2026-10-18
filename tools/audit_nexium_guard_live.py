#!/usr/bin/env python3
"""Audit NRO-recorded *live manual* guard alert and first contact damage.

The guest may not substitute the offscreen scripted combat test for these
events: this file is written only after the actual pad-driven game.tick().
"""
import argparse
from pathlib import Path
import re

MARKER = "VPD_ROMFREE_GUARD_LIVE_V1"
EVENTS = ("alert", "strike")
FIELDS = ("seq","event","frame","player_x","guard_x","player_hp",
          "guard_hp","attacks","cooldown","alerted","input_right",
          "source","original_game_proven")


def verify(raw):
    if not isinstance(raw,bytes) or not raw or len(raw)>640:
        raise ValueError("live manual guest trace missing or too large")
    text=raw.decode("ascii")
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise ValueError("invalid live guard witness termination")
    lines=text.splitlines()
    if len(lines)!=2:
        raise ValueError("need precisely two real manual guard transitions")
    frames=[]
    for seq,(event,line) in enumerate(zip(EVENTS,lines),1):
        tokens=line.split(" ")
        if len(tokens)!=len(FIELDS)+1 or tokens[0]!=MARKER:
            raise ValueError("invalid manual combat record marker/schema size")
        parts=[t.split("=",1) for t in tokens[1:]]
        if any(len(p)!=2 for p in parts) or tuple(p[0] for p in parts)!=FIELDS:
            raise ValueError("manual combat field order invalid")
        row=dict(parts)
        if row["seq"]!=str(seq) or row["event"]!=event or (
            row["source"]!="live_guest" or
            row["input_right"]!="1" or
            row["original_game_proven"]!="no"
        ):
            raise ValueError("not an ordered genuine live guest input event")
        for key in ("frame","player_x","guard_x","player_hp","guard_hp",
                    "attacks","cooldown","alerted"):
            if not re.fullmatch(r"0|[1-9][0-9]*",row[key]):
                raise ValueError("noncanonical manual guard numeric value")
        frame=int(row["frame"])
        px=int(row["player_x"])
        gx=int(row["guard_x"])
        if not 1<=frame<=1200 or not 0<=px<=64*16*256 or (
            not 14*16*256<=gx<=20*16*256 or gx%256
        ):
            raise ValueError("live guard frame or positions out of bounds")
        if abs(px-gx)>(144 if seq==1 else 20)*256:
            raise ValueError("guard detection/contact is outside gameplay radius")
        hp=int(row["player_hp"])
        attacks=int(row["attacks"])
        cd=int(row["cooldown"])
        expected=(5,0,0) if seq==1 else (4,1,32)
        if (hp,attacks,cd)!=expected:
            raise ValueError("guard damage and attack cooldown not observed")
        if row["guard_hp"]!="3" or row["alerted"]!="1":
            raise ValueError("guard defeated or not alerted in live trace")
        frames.append(frame)
    if frames[1]<=frames[0]:
        raise ValueError("strike must occur after first proximity alert")
    return {"alert_frame":frames[0],"strike_frame":frames[1]}


def audit(folder):
    base=Path(folder)
    trace=base/"guest-guard-live-witness.txt"
    if not trace.is_file():
        raise ValueError("actual NeXium manual encounter trace not found")
    result=verify(trace.read_bytes())
    host=base/"input-probe.txt"
    if not host.is_file() or (
        "host_guard_live_move_sent=yes key=D duration=3.4s" not in
        host.read_text(encoding="ascii").splitlines()
    ):
        raise ValueError("real NeXium right-direction trial was not injected")
    prerequisites=(
        ("manual-result.txt","VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "),
        ("dash-result.txt","VPD_NEXIUM_GUEST_DASH_PASS "),
        ("guard-result.txt","VPD_NEXIUM_GUARD_PATROL_PASS "),
        ("guard-combat-result.txt","VPD_NEXIUM_GUARD_COMBAT_SCRIPT_PASS "),
        ("native-exit-result.txt","VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
    )
    for name,header in prerequisites:
        file=base/name
        if not file.is_file() or not file.read_text(encoding="ascii").startswith(header):
            raise ValueError("missing independent guest proof "+name)
    output=(
        "VPD_NEXIUM_GUARD_LIVE_CONTACT_PASS "
        f"alert_frame={result['alert_frame']} "
        f"strike_frame={result['strike_frame']} "
        "input_right=yes alert=yes first_melee_damage=yes "
        "hero_hp=4 melee_cooldown=32 source=live_guest "
        "manual_kill_proven=no original_game_proven=no\n"
    )
    (base/"guard-live-result.txt").write_text(output,encoding="ascii")
    print(output,end="")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    args=parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError,UnicodeError,ValueError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"guard-live-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        parser.exit(1,"NeXium live guard input unverified: "+str(exc)+"\n")
