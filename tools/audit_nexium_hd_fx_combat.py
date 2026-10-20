#!/usr/bin/env python3
"""Real live fourth-guard L+R: genuine post-hit source and independent X11 images."""
import argparse
from pathlib import Path
import re
from audit_nexium_fourth_stage import raster

RECORD=re.compile(
    r"^VPD_HD_FX_COMBAT_V1 seq=([12]) mode=(off|on) frame=([0-9]+) "
    r"manual=1 l=1 r=1 edge=1 "
    r"guard_health=2 guard_hits=1 hero_health=([1-5]) "
    r"wave_active=0 stage_clear=0 "
    r"scene_other=([0-9a-f]{16}) scene_displayed=([0-9a-f]{16}) "
    r"roi_pixels=414000 simulation_before=([0-9a-f]{16}) "
    r"simulation_after=([0-9a-f]{16}) "
    r"source=libnx_pad same_frame=yes$"
)

def verify(raw):
    if not isinstance(raw,bytes) or len(raw)>1150 or not raw.endswith(b"\n"):
        raise ValueError("live combat guest trace missing/truncated/oversized")
    try:
        lines=raw.decode("ascii").splitlines()
    except UnicodeError as e:
        raise ValueError("combat witness non-ASCII") from e
    if len(lines)!=2:
        raise ValueError("exactly two real combat L+R transitions required")
    results=[]
    for index,line in enumerate(lines):
        match=RECORD.fullmatch(line)
        if not match:
            raise ValueError("malformed source combat L+R record")
        seq,mode,frame,health,other,actual,sim_before,sim_after=match.groups()
        if int(seq)!=index+1 or mode!=("off" if index==0 else "on"):
            raise ValueError("combat L+R sequence/order invalid")
        if int(frame)<=0 or other==actual:
            raise ValueError("combat HD mode not proven by scene pixels")
        if sim_before!=sim_after:
            raise ValueError("combat HD raster mutated authoritative simulation")
        results.append(int(frame))
    if results[1]<=results[0]:
        raise ValueError("combat pad edges not frame ordered")
    return results

def audit(base):
    base=Path(base)
    prior=(base/"fourth-combat-result.txt").read_text("ascii")
    if not prior.startswith("VPD_NEXIUM_FOURTH_COMBAT_PASS "):
        raise ValueError("real fourth guard hit was not verified")
    hit=re.search(r"\bhit_frame=(\d+)\b",prior)
    if not hit:
        raise ValueError("fourth guard impact frame absent")
    proof=base/"guest-hd-fx-combat-witness.txt"
    if not proof.is_file():
        raise ValueError("native combat L+R guest SD witness missing")
    frames=verify(proof.read_bytes())
    if frames[0]<=int(hit.group(1)):
        raise ValueError("combat L+R preceded first real guard projectile hit")
    clear=(base/"fourth-guard-clear-result.txt").read_text("ascii")
    if not clear.startswith("VPD_NEXIUM_FOURTH_GUARD_CLEAR_PASS "):
        raise ValueError("fourth guard kill absent")
    killed=re.search(r"\bframe=(\d+)\b",clear)
    if not killed or frames[1]>=int(killed.group(1)):
        raise ValueError("combat L+R not executed before guard defeat")
    host=(base/"input-probe.txt").read_text("ascii").splitlines()
    visual=(base/"visual-probe.txt").read_text("ascii").splitlines()
    for mode in ("off","on"):
        event=f"host_combat_hd_fx_chord_sent=yes keys=Q+E expected={mode} guest_seen=yes"
        snap=f"capture=screen-live-combat-hd-fx-{mode}"
        if host.count(event)!=1 or visual.count(snap)!=1:
            raise ValueError("missing uniquely paired actual combat pad/X11 witness")
    off,hash_off=raster(base,"screen-live-combat-hd-fx-off")
    on,hash_on=raster(base,"screen-live-combat-hd-fx-on")
    different=0
    for y in range(185,245):
        for x in range(945,1240):
            pos=(y*1280+x)*3
            if off[pos:pos+3]!=on[pos:pos+3]:
                different+=1
    if different<10 or hash_off==hash_on:
        raise ValueError("actual X11 combat HD status did not change")
    report=(
        "VPD_NEXIUM_HD_FX_COMBAT_PASS "
        f"off_frame={frames[0]} on_frame={frames[1]} "
        "guard_alive_both=yes guard_health=2 guard_hits=1 "
        "real_pad_chords=2 guest_simulation_unchanged=yes "
        "roi_pixels=414000 active_combat=yes "
        f"status_x11_changed_pixels={different} "
        f"off_ppm_sha256={hash_off} on_ppm_sha256={hash_on} "
        "source=libnx_pad native_x11_evidence=yes "
        "original_game_proven=no physical_switch_proven=no\n"
    )
    (base/"hd-fx-combat-result.txt").write_text(report,encoding="ascii")
    print(report,end="")
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    args=parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError,ValueError,UnicodeError) as e:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"hd-fx-combat-result.txt").write_text(
            "INCONCLUSIVE: "+str(e)+"\n",encoding="ascii")
        parser.exit(1,"Live combat native HD FX witness unverified: "+str(e)+"\n")
