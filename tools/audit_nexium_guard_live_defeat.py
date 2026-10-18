#!/usr/bin/env python3
"""Fail-closed independent audit of native manual Fire and guard defeat.

The evidence is written by the *live, pad-driven* game core, not by the
host-triggered internal simulation or an offline-generated example.
"""
import argparse
from pathlib import Path
import re

PREFIX = "VPD_ROMFREE_GUARD_LIVE_DEFEAT_V1"
FIELDS = ("seq", "event", "frame", "player_x", "guard_x", "hp_before",
          "hp_after", "hits_before", "hits_after", "shots",
          "input_fire", "source", "original_game_proven")


def verify(raw):
    if not isinstance(raw,bytes) or not raw or len(raw)>1400:
        raise ValueError("live guard defeat witness absent or oversized")
    txt=raw.decode("ascii")
    if not txt.endswith("\n") or "\r" in txt or "\x00" in txt:
        raise ValueError("invalid live defeat record termination")
    rows=txt.splitlines()
    if not 2<=len(rows)<=4:
        raise ValueError("one genuine shot and one to three impacts required")
    previous=None
    first_hp=None
    first_frame=None
    for number,line in enumerate(rows,1):
        fields=line.split(" ")
        if len(fields)!=len(FIELDS)+1 or fields[0]!=PREFIX:
            raise ValueError("incorrect live guard defeat record format")
        pairs=[field.split("=",1) for field in fields[1:]]
        if any(len(pair)!=2 for pair in pairs) or (
            tuple(pair[0] for pair in pairs)!=FIELDS
        ):
            raise ValueError("invalid live defeat field order")
        entry=dict(pairs)
        if (entry["seq"]!=str(number) or
            entry["source"]!="live_guest" or
            entry["original_game_proven"]!="no"):
            raise ValueError("wrong source or sequence")
        for key in ("frame","player_x","guard_x","hp_before","hp_after",
                    "hits_before","hits_after","shots","input_fire"):
            if not re.fullmatch(r"0|[1-9][0-9]*",entry[key]):
                raise ValueError("noncanonical numeric event field")
        values={key:int(entry[key]) for key in (
            "frame","player_x","guard_x","hp_before","hp_after",
            "hits_before","hits_after","shots","input_fire"
        )}
        f=values["frame"]
        px=values["player_x"]
        gx=values["guard_x"]
        before=values["hp_before"]
        after=values["hp_after"]
        hb=values["hits_before"]
        ha=values["hits_after"]
        shots=values["shots"]
        fire=values["input_fire"]
        if (not 1<=f<=1200 or not 0<=px<=64*16*256 or
            not 14*16*256<=gx<=20*16*256 or gx%256 or
            not 0<=after<=3 or not 1<=before<=3 or
            hb>3 or ha>3 or not 1<=shots<=100 or fire not in (0,1)):
            raise ValueError("impossible guard scene state")
        if before+hb!=3 or after+ha!=3:
            raise ValueError("guard health and verified hit counter disagree")
        if number==1:
            if (entry["event"]!="fire" or fire!=1 or
                before!=after or hb!=ha or gx<=px):
                raise ValueError("no real right-facing Fire step")
            first_hp=before
            first_frame=f
        else:
            if (entry["event"]!=("defeat" if number==len(rows) else "impact") or
                before!=previous["hp_after"] or
                hb!=previous["hits_after"] or after!=before-1 or
                ha!=hb+1 or f<=previous["frame"] or
                shots<previous["shots"]):
                raise ValueError("projectile hit not linked to previous state")
            if number==len(rows) and after!=0:
                raise ValueError("last guest event did not defeat the guard")
        previous=values
    if len(rows)!=first_hp+1:
        raise ValueError("wrong number of impacts for initially observed HP")
    return {"fire_frame":first_frame, "defeat_frame":previous["frame"],
            "impacts":len(rows)-1,"start_hp":first_hp,
            "final_hits":previous["hits_after"]}


def audit(folder):
    root=Path(folder)
    witness=root/"guest-guard-live-defeat-witness.txt"
    if not witness.is_file():
        raise ValueError("guest did not record player-controlled guard defeat")
    data=verify(witness.read_bytes())
    host=root/"input-probe.txt"
    if not host.is_file() or (
        "host_guard_live_fire_sent=yes key=Z after_guest_strike=yes"
        not in host.read_text(encoding="ascii").splitlines()
    ):
        raise ValueError("host did not submit separate live manual Fire trial")
    prerequisites=(
        ("manual-result.txt","VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "),
        ("dash-result.txt","VPD_NEXIUM_GUEST_DASH_PASS "),
        ("guard-result.txt","VPD_NEXIUM_GUARD_PATROL_PASS "),
        ("guard-combat-result.txt","VPD_NEXIUM_GUARD_COMBAT_SCRIPT_PASS "),
        ("guard-live-result.txt","VPD_NEXIUM_GUARD_LIVE_CONTACT_PASS "),
        ("native-exit-result.txt","VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
    )
    for name,marker in prerequisites:
        path=root/name
        if not path.is_file() or not path.read_text(
            encoding="ascii").startswith(marker):
            raise ValueError("independent native prerequisite missing: "+name)
    manual=root/"guest-guard-live-witness.txt"
    if not manual.is_file() or len(manual.read_bytes())>640:
        raise ValueError("linked live contact witness missing")
    records=manual.read_text(encoding="ascii").splitlines()
    if len(records)!=2 or not records[1].startswith(
        "VPD_ROMFREE_GUARD_LIVE_V1 seq=2 event=strike "):
        raise ValueError("invalid original guest strike linkage")
    strike_frame_match=re.search(r"\bframe=([0-9]+)\b",records[1])
    guard_hp_match=re.search(r"\bguard_hp=([0-9]+)\b",records[1])
    if (not strike_frame_match or not guard_hp_match or
        data["fire_frame"]<=int(strike_frame_match.group(1)) or
        data["start_hp"]>int(guard_hp_match.group(1))):
        raise ValueError("guard defeat does not follow native live strike")
    report=(
        "VPD_NEXIUM_GUARD_LIVE_DEFEAT_PASS "
        f"fire_frame={data['fire_frame']} defeat_frame={data['defeat_frame']} "
        f"verified_impacts={data['impacts']} "
        f"initial_guard_hp={data['start_hp']} "
        f"cumulative_hits={data['final_hits']} "
        "manual_fire_input=yes guard_defeated=yes "
        "source=live_guest original_game_proven=no\n"
    )
    (root/"guard-live-defeat-result.txt").write_text(report,encoding="ascii")
    print(report,end="")
    return data

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--evidence",type=Path,required=True)
    args=ap.parse_args()
    try:
        audit(args.evidence)
    except (OSError,ValueError,UnicodeError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"guard-live-defeat-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        ap.exit(1,"Live manual guard defeat unverified: "+str(exc)+"\n")
