#!/usr/bin/env python3
"""Strict live NeXium attestation of explicit Minus replay after stage win."""
import argparse
import hashlib
from pathlib import Path
import re

PREFIX="VPD_ROMFREE_MANUAL_RETRY_V1"
FIELDS=("event","reason","old_frame","old_hp","old_guard_hp",
        "old_sentry_hp","old_clear","new_frame","new_x","new_hp",
        "new_guard_hp","new_sentry_hp","wave","clear","input_minus",
        "source","original_game_proven")
NUMS=("old_frame","old_hp","old_guard_hp","old_sentry_hp","old_clear",
      "new_frame","new_x","new_hp","new_guard_hp","new_sentry_hp",
      "wave","clear","input_minus")

def parse_guest(raw):
    if not isinstance(raw,bytes) or not raw or len(raw)>500:
        raise ValueError("missing, duplicate or oversized native Minus record")
    line=raw.decode("ascii")
    if not line.endswith("\n") or line.count("\n")!=1 or "\r" in line:
        raise ValueError("exactly one canonical native record required")
    fields=line[:-1].split(" ")
    if len(fields)!=len(FIELDS)+1 or fields[0]!=PREFIX:
        raise ValueError("invalid guest retry marker or shape")
    pairs=[v.split("=",1) for v in fields[1:]]
    if any(len(p)!=2 for p in pairs) or tuple(p[0] for p in pairs)!=FIELDS:
        raise ValueError("incorrect guest restart schema or order")
    row=dict(pairs)
    if (row["event"]!="restart" or row["reason"]!="victory" or
        row["source"]!="live_guest" or
        row["original_game_proven"]!="no"):
        raise ValueError("not the live pad-driven victory restart")
    for key in NUMS:
        if not re.fullmatch(r"0|[1-9][0-9]*",row[key]):
            raise ValueError("invalid guest retry numeric field")
    v={key:int(row[key]) for key in NUMS}
    if (not 1<=v["old_frame"]<=2000 or not 1<=v["old_hp"]<=5 or
        v["old_guard_hp"]!=0 or v["old_sentry_hp"]!=0 or
        v["old_clear"]!=1 or v["new_frame"]!=0 or
        v["new_x"]!=3*16*256 or v["new_hp"]!=5 or
        v["new_guard_hp"]!=3 or v["new_sentry_hp"]!=2 or
        v["wave"]!=0 or v["clear"]!=0 or v["input_minus"]!=1):
        raise ValueError("victory state not reset to an authentic new level")
    return v

def audit(directory):
    root=Path(directory)
    guest=root/"guest-manual-retry-witness.txt"
    if not guest.is_file():
        raise ValueError("running Switch NRO did not write a manual retry")
    values=parse_guest(guest.read_bytes())
    host=root/"input-probe.txt"
    if not host.is_file():
        raise ValueError("no independent X11 input log")
    lines=host.read_text(encoding="ascii").splitlines()
    if not all(mark in lines for mark in (
        "host_second_wave_controls_sent=yes keys=D+Z guest_exit=yes",
        "host_manual_retry_key_sent=yes key=N expected=Minus",
        "host_manual_retry_guest_observed=yes",
    )):
        raise ValueError("actual NeXium Minus key after native victory unverified")
    for name,stamp in (
        ("manual-result.txt","VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "),
        ("second-wave-live-result.txt","VPD_NEXIUM_SECOND_WAVE_LIVE_PASS "),
        ("guard-live-raster-result.txt","VPD_NEXIUM_GUARD_LIVE_RASTER_PASS "),
        ("native-exit-result.txt","VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
    ):
        file=root/name
        if not file.is_file() or not file.read_text(encoding="ascii").startswith(stamp):
            raise ValueError("mandatory native prerequisite missing: "+name)
    cleared=(root/"second-wave-live-result.txt").read_text(encoding="ascii")
    match=re.search(r"(?:^| )exit_frame=([1-9][0-9]*)(?: |$)",cleared)
    if not match or values["old_frame"]<int(match.group(1)):
        raise ValueError("retry did not happen after the same guest stage exit")
    progress=root/"visual-probe.txt"
    if not progress.is_file() or (
        "live_manual_restart_raster_after_guest_event=yes"
        not in progress.read_text(encoding="ascii").splitlines()
    ):
        raise ValueError("no X11 screenshot after actual guest restart")
    scans=[]
    for scene in ("stage-clear","restart"):
        name=f"screen-live-{scene}"
        png=root/(name+".png")
        ppm=root/(name+".ppm")
        if not png.is_file() or not png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("native X11 PNG missing: "+name)
        if not ppm.is_file():
            raise ValueError("native X11 PPM missing: "+name)
        b=ppm.read_bytes()
        # ImageMagick's genuine xwd->P6 path emits "#xwdump" as a
        # header comment. Require exact 1280x720 payload despite comments.
        header=re.match(
            rb"\\AP6\\n(?:\\#[ -~]{1,200}\\n){0,3}1280 720\\n255\\n",b
        )
        if not header or len(b)!=header.end()+1280*720*3:
            raise ValueError("invalid native X11 P6 raster: "+name)
        scans.append(b)
    if scans[0]==scans[1]:
        raise ValueError("guest retry did not visibly reset the playfield")
    msg=(
        "VPD_NEXIUM_MANUAL_RETRY_PASS "
        f"old_frame={values['old_frame']} old_hp={values['old_hp']} "
        "reason=victory real_pad_minus=yes new_frame=0 new_hp=5 "
        "guard_restored=3 sentry_restored=2 wave_reset=yes "
        f"clear_sha256={hashlib.sha256(scans[0]).hexdigest()} "
        f"retry_sha256={hashlib.sha256(scans[1]).hexdigest()} "
        "actual_x11_reset=yes physical_switch_proven=no "
        "original_game_proven=no\n"
    )
    (root/"manual-retry-result.txt").write_text(msg,encoding="ascii")
    print(msg,end="")
    return values

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    args=parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError,UnicodeError,ValueError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"manual-retry-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        parser.exit(1,"Native manual replay unverified: "+str(exc)+"\n")
