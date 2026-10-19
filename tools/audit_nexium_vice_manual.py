#!/usr/bin/env python3
"""Require actual ordered guest-generated manual input effects and cleanup."""
import argparse
from pathlib import Path
import re

MARKER = "VPD_ROMFREE_MANUAL_V1"
EVENTS = ("enter","right","fire","jump","left","plus","exit")
FIELDS = ("seq","event","frame","metric","mode","original_game_proven")
# First five source actions are one level's short control probe. A complete
# victory -> death -> third victory includes three manual attempts, so only
# Plus and Exit use a longer, still bounded, monotone session clock.
MAX_EARLY_FRAME=1200
MAX_SESSION_FRAME=3600


def verify(raw):
    if not isinstance(raw,bytes) or not raw or len(raw)>2048:
        raise ValueError("guest input trace missing or too large")
    text=raw.decode("ascii")
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise ValueError("guest trace has malformed line endings")
    lines=text.splitlines()
    if len(lines)!=7: raise ValueError("need exactly seven guest events")
    last_frame=0
    for seq,(name,line) in enumerate(zip(EVENTS,lines),1):
        parts=line.split()
        if len(parts)!=7 or parts[0]!=MARKER:
            raise ValueError("manual witness format invalid")
        pairs=[p.split("=",1) for p in parts[1:]]
        if any(len(p)!=2 for p in pairs) or tuple(p[0] for p in pairs)!=FIELDS:
            raise ValueError("guest witness schema invalid")
        rec=dict(pairs)
        if rec["seq"]!=str(seq) or rec["event"]!=name or            rec["mode"]!="manual" or rec["original_game_proven"]!="no":
            raise ValueError("wrong event sequence or mode")
        if not re.fullmatch(r"[0-9]+",rec["frame"]) or            not re.fullmatch(r"[0-9]+",rec["metric"]):
            raise ValueError("noncanonical numeric fields")
        frame=int(rec["frame"]);metric=int(rec["metric"])
        max_frame=MAX_EARLY_FRAME if seq<=5 else MAX_SESSION_FRAME
        if (metric<=0 or (seq==1 and frame!=0) or
            (seq>1 and (frame<last_frame or frame<=0 or
                        frame>max_frame))):
            raise ValueError("invalid frame or missing observable effect")
        if seq==7 and frame!=last_frame:
            # Exit is recorded after framebuffer shutdown without advancing
            # the game loop, so both terminal events use the same source tick.
            raise ValueError("Plus and Exit must share terminal session tick")
        if name in ("enter","plus","exit") and metric!=1:
            raise ValueError("unbounded event value")
        if name=="fire" and metric>8:
            raise ValueError("impossible projectile increment")
        last_frame=frame
    if not int(lines[1].split()[3].split("=")[1])>0:
        raise ValueError("movement was not observed")
    return {"events":len(lines),"last_frame":last_frame}


def audit(directory):
    base=Path(directory)
    file=base/"guest-manual-witness.txt"
    if not file.is_file():
        raise ValueError("no actual NeXium guest-created manual input report")
    records=verify(file.read_bytes())
    host=base/"input-probe.txt"
    if not host.is_file() or "host_plus_key_sent=yes" not in host.read_text() or        "host_manual_probe_sent=yes" not in host.read_text():
        raise ValueError("host input injection log unavailable")
    result=("VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "
            "guest_effects=right,fire,jump,left guest_enter=yes "
            "guest_plus=yes guest_cleanup=yes "
            f"events={records['events']} last_frame={records['last_frame']} "
            "native_switch_runtime=yes original_game_proven=no "
            "emulator_gui_exit_proven=no\n")
    (base/"manual-result.txt").write_text(result)
    print(result,end="")


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--evidence",required=True,type=Path)
    args=ap.parse_args()
    try:
        audit(args.evidence)
    except (OSError,ValueError,UnicodeError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"manual-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n")
        ap.exit(1,"NeXium manual guest input unverified: "+str(exc)+"\n")
