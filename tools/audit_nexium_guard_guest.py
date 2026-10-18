#!/usr/bin/env python3
"""Strict audit of actual NeXium guest-generated guard patrol milestones."""
import argparse
from pathlib import Path
import re

EVENTS = ("first", "patrol")
FIELDS = ("seq", "event", "frame", "x_fixed", "hp",
          "alerted", "source", "original_game_proven")


def verify(raw):
    if not isinstance(raw, bytes) or not raw or len(raw)>512:
        raise ValueError("guard witness absent or oversized")
    decoded=raw.decode("ascii")
    if not decoded.endswith("\n") or "\r" in decoded or "\x00" in decoded:
        raise ValueError("malformed guard witness termination")
    lines=decoded.splitlines()
    if len(lines)!=2:
        raise ValueError("expected exactly two guest guard events")
    expected_x=(65792,67584)
    for idx, (event, line) in enumerate(zip(EVENTS,lines),1):
        fields=line.split(" ")
        if len(fields)!=9 or fields[0]!="VPD_ROMFREE_GUARD_V1":
            raise ValueError("wrong guard witness line format")
        kv=[field.split("=",1) for field in fields[1:]]
        if any(len(pair)!=2 for pair in kv) or (
            tuple(key for key,value in kv)!=FIELDS
        ):
            raise ValueError("wrong field order in guard witness")
        row=dict(kv)
        if row["seq"]!=str(idx) or row["event"]!=event:
            raise ValueError("unexpected guard event order")
        if row["source"]!="guest" or row["original_game_proven"]!="no":
            raise ValueError("host or original-game witness forgery")
        for key in ("frame","x_fixed","hp","alerted"):
            if not re.fullmatch(r"0|[1-9][0-9]*",row[key]):
                raise ValueError("noncanonical guard numeric field")
        if int(row["frame"])!=(1 if idx==1 else 8) or (
            int(row["x_fixed"])!=expected_x[idx-1]
        ) or row["hp"]!="3" or row["alerted"]!="0":
            raise ValueError("guard did not reach exact native AI milestone")
    return {"first_frame":1, "patrol_frame":8}


def audit(directory):
    base=Path(directory)
    path=base/"guest-guard-witness.txt"
    if not path.is_file():
        raise ValueError("native guard SD evidence missing")
    result=verify(path.read_bytes())
    for file,prefix in (
        ("manual-result.txt","VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "),
        ("native-exit-result.txt","VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
        ("dash-result.txt","VPD_NEXIUM_GUEST_DASH_PASS "),
    ):
        found=base/file
        if not found.is_file() or not found.read_text(
            encoding="ascii").startswith(prefix):
            raise ValueError("independent native prerequisite absent: "+file)
    output=(
        "VPD_NEXIUM_GUARD_PATROL_PASS enemy_spawn=yes "
        "guest_first_step=yes guest_patrol=yes "
        "frames=1,8 x_fixed=65792,67584 "
        "enemy_health=3 guest_sd_witness=yes "
        "host_render_proven=no original_game_proven=no\n"
    )
    (base/"guard-result.txt").write_text(output,encoding="ascii")
    print(output,end="")
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",required=True,type=Path)
    args=parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError,ValueError,UnicodeError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"guard-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        parser.exit(1,"NeXium guard encounter unverified: "+str(exc)+"\n")
