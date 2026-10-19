#!/usr/bin/env python3
"""Audit two *real* native NeXium retries: victory, then guard-caused defeat.

This test must see host X11 input + two exact guest SD state transitions and
actual X11 pixels. It cannot be passed by the older offscreen guest script.
"""
import argparse
import hashlib
from pathlib import Path
import re

PREFIX="VPD_ROMFREE_DEFEAT_RETRY_V1"
EVENTS=("contact","death","restart")
KEYS=("seq","event","frame","hero_x","hero_hp","guard_hp",
      "guard_attacks","sentry_hp","wave","clear","input_right",
      "input_minus","old_frame","old_hp","source","original_game_proven")
NUMS=("frame","hero_x","hero_hp","guard_hp","guard_attacks",
      "sentry_hp","wave","clear","input_right","input_minus",
      "old_frame","old_hp")
P6HEADER=re.compile(rb"\AP6\n(?:\#[ -~]{1,200}\n){0,3}1280 720\n255\n")

def verify(raw):
    if not isinstance(raw,bytes) or not raw or len(raw)>1500:
        raise ValueError("missing or oversized native second-retry witness")
    s=raw.decode("ascii")
    if not s.endswith("\n") or "\r" in s or "\x00" in s:
        raise ValueError("invalid guest witness line endings")
    lines=s.splitlines()
    if len(lines)!=3:
        raise ValueError("exactly three live post-win guard/replay events required")
    rows=[]
    for seq,(event,line) in enumerate(zip(EVENTS,lines),1):
        cols=line.split(" ")
        if cols[0]!=PREFIX or len(cols)!=len(KEYS)+1:
            raise ValueError("invalid native defeat witness shape")
        pairs=[c.split("=",1) for c in cols[1:]]
        if any(len(x)!=2 for x in pairs) or (
            tuple(x[0] for x in pairs)!=KEYS
        ):
            raise ValueError("incorrect defeat witness key order")
        row=dict(pairs)
        if (row["seq"]!=str(seq) or row["event"]!=event or
            row["source"]!="live_guest" or
            row["original_game_proven"]!="no"):
            raise ValueError("incorrect native defeat source/progression")
        for key in NUMS:
            if not re.fullmatch(r"0|[1-9][0-9]*",row[key]):
                raise ValueError("noncanonical numeric defeat input/state")
        v={key:int(row[key]) for key in NUMS}
        if (v["frame"]>1200 or v["hero_x"]>64*16*256 or
            v["hero_hp"]>5 or v["guard_hp"]>3 or
            v["sentry_hp"]>2 or v["guard_attacks"]>50 or
            v["wave"] not in (0,1) or v["clear"] not in (0,1) or
            v["input_right"] not in (0,1) or
            v["input_minus"] not in (0,1) or v["old_hp"]>5):
            raise ValueError("impossible new-run guard or restart state")
        rows.append(v)
    contact,death,restart=rows
    if (contact["frame"]<1 or contact["hero_hp"]!=4 or
        contact["guard_hp"]!=3 or contact["guard_attacks"]!=1 or
        contact["sentry_hp"]!=2 or contact["wave"] or contact["clear"] or
        contact["input_right"]!=1 or contact["input_minus"]!=0 or
        contact["old_frame"] or contact["old_hp"]):
        raise ValueError("second-playthrough source melee contact missing")
    if (death["frame"]<=contact["frame"] or death["hero_hp"]!=0 or
        death["guard_hp"]!=3 or death["guard_attacks"]<5 or
        death["sentry_hp"]!=2 or death["wave"] or death["clear"] or
        death["input_minus"]!=0 or death["old_frame"] or death["old_hp"]):
        raise ValueError("source guard did not actually kill the hero")
    if (restart["frame"]!=0 or restart["hero_x"]!=3*16*256 or
        restart["hero_hp"]!=5 or restart["guard_hp"]!=3 or
        restart["guard_attacks"]!=0 or restart["sentry_hp"]!=2 or
        restart["wave"] or restart["clear"] or
        restart["input_right"]!=0 or restart["input_minus"]!=1 or
        restart["old_hp"]!=0 or
        not death["frame"]<=restart["old_frame"]<=death["frame"]+100):
        raise ValueError("real Minus did not cleanly restart defeated run")
    return {"contact_frame":contact["frame"],
            "death_frame":death["frame"],
            "restart_source_frame":restart["old_frame"]}

def audit(directory):
    base=Path(directory)
    guest=base/"guest-live-defeat-retry-witness.txt"
    if not guest.is_file():
        raise ValueError("guest did not create second-run live defeat trace")
    values=verify(guest.read_bytes())
    host=base/"input-probe.txt"
    if not host.is_file():
        raise ValueError("no X11 controller evidence")
    lines=host.read_text(encoding="ascii").splitlines()
    required=(
        "host_manual_retry_guest_observed=yes",
        "host_post_victory_guard_contact_sent=yes key=D observed=yes",
        "host_guard_death_observed=yes",
        "host_defeat_minus_key_sent=yes key=N expected=Minus",
        "host_defeat_retry_guest_observed=yes",
    )
    if any(x not in lines for x in required):
        raise ValueError("real Right/Minus sequence after first replay unverified")
    for name,stamp in (
        ("manual-result.txt","VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "),
        ("manual-retry-result.txt","VPD_NEXIUM_MANUAL_RETRY_PASS "),
        ("second-wave-live-result.txt","VPD_NEXIUM_SECOND_WAVE_LIVE_PASS "),
        ("native-exit-result.txt","VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
    ):
        file=base/name
        if not file.is_file() or not file.read_text(encoding="ascii").startswith(stamp):
            raise ValueError("prior required guest proof missing: "+name)
    first=base/"guest-manual-retry-witness.txt"
    if not first.is_file() or b"reason=victory " not in first.read_bytes():
        raise ValueError("source first-stage victory replay not independently confirmed")
    trace=base/"visual-probe.txt"
    if not trace.is_file():
        raise ValueError("real X11 capture timeline absent")
    events=trace.read_text(encoding="ascii").splitlines()
    for mark in (
        "live_game_over_raster_after_guest_death=yes",
        "live_defeat_replay_raster_after_guest_event=yes",
        "capture=screen-live-game-over",
        "capture=screen-live-defeat-restart",
    ):
        if mark not in events:
            raise ValueError("native death/retry screenshot not event-aligned: "+mark)
    rasters=[]
    digests=[]
    for suffix in ("game-over","defeat-restart"):
        key="screen-live-"+suffix
        png=base/(key+".png")
        ppm=base/(key+".ppm")
        if not png.is_file() or not png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("real X11 PNG missing: "+key)
        if not ppm.is_file():
            raise ValueError("real X11 P6 file missing: "+key)
        raw=ppm.read_bytes()
        h=P6HEADER.match(raw)
        if not h or len(raw)!=h.end()+3*1280*720:
            raise ValueError("invalid or cropped 1280x720 NeXium framebuffer")
        rasters.append(raw[h.end():])
        digests.append(hashlib.sha256(raw).hexdigest())
    before,after=rasters
    # The game-over screen occupies a grounded 570x168 centered region.
    # FPS chrome or unrelated moving background cannot count as evidence.
    count=0
    for y in range(230,395):
        start=(y*1280+355)*3
        stop=(y*1280+925)*3
        aa=before[start:stop]
        bb=after[start:stop]
        count+=sum(aa[n:n+3]!=bb[n:n+3] for n in range(0,len(aa),3))
    if count<500:
        raise ValueError("the central defeat overlay did not clear after Minus")
    result=(
        "VPD_NEXIUM_DEFEAT_RETRY_PASS "
        f"contact_frame={values['contact_frame']} "
        f"death_frame={values['death_frame']} "
        f"old_frame={values['restart_source_frame']} "
        "guard_attacks_at_death=at_least_5 old_hp=0 "
        "real_pad_right=yes real_pad_minus=yes "
        "reset_hp=5 reset_guard_hp=3 reset_sentry_hp=2 "
        f"changed_center_pixels={count} "
        f"death_ppm_sha256={digests[0]} "
        f"replay_ppm_sha256={digests[1]} "
        "native_x11_evidence=yes original_game_proven=no "
        "physical_switch_proven=no\n"
    )
    (base/"defeat-retry-result.txt").write_text(result,encoding="ascii")
    print(result,end="")
    return values

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    args=parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError,UnicodeError,ValueError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"defeat-retry-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        parser.exit(1,"Real native guard defeat and replay unverified: "+str(exc)+"\n")
