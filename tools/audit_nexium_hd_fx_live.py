#!/usr/bin/env python3
"""Strict NeXium V1 proof of two real HD-toggle pad edges DURING wave combat."""
import argparse
from pathlib import Path
import re

from audit_nexium_fourth_stage import raster

EVENT=re.compile(
    r"^VPD_HD_FX_LIVE_V1 seq=([12]) mode=(off|on) frame=([0-9]+) "
    r"right=1 fire=1 moving=1 wave=1 guard_dead=1 "
    r"sentry_hp=([12]) hero_dx_fixed=512 "
    r"scene_other=([0-9a-f]{16}) scene_displayed=([0-9a-f]{16}) "
    r"roi_pixels=414000 simulation_before=([0-9a-f]{16}) "
    r"simulation_after=([0-9a-f]{16}) source=libnx_pad same_frame=yes$"
)

def verify(raw):
    if not isinstance(raw, bytes) or not raw.endswith(b"\n") or len(raw)>1200:
        raise ValueError("live-combat native guest witness missing or truncated")
    try:
        lines=raw.decode("ascii").splitlines()
    except UnicodeError as exc:
        raise ValueError("live-combat witness is not ASCII") from exc
    if len(lines)!=2:
        raise ValueError("exactly two live combat pad toggles required")
    rows=[]
    for i,line in enumerate(lines):
        m=EVENT.fullmatch(line)
        if not m:
            raise ValueError("invalid real guest active-wave toggle format")
        seq,mode,frame,sentry,other,shown,sim_before,sim_after=m.groups()
        if int(seq)!=i+1 or mode!=("off" if i==0 else "on"):
            raise ValueError("active-wave pad transitions out of order")
        if int(frame)<=0 or other==shown:
            raise ValueError("no independent rendered scene pixel delta")
        if sim_before!=sim_after:
            raise ValueError("HD rendering changed real game simulation")
        rows.append((int(frame),int(sentry),sim_before))
    if rows[1][0]<=rows[0][0]:
        raise ValueError("active combat game frames not strictly increasing")
    return rows

def audit(base):
    base=Path(base)
    prior=(base/"fourth-stage-result.txt").read_text(encoding="ascii")
    if not prior.startswith("VPD_NEXIUM_FOURTH_STAGE_PASS "):
        raise ValueError("real fourth wave+stage exit is not independently proven")
    wave=re.search(r"\bwave_frame=(\d+)\b",prior)
    exit_event=re.search(r"\bexit_frame=(\d+)\b",prior)
    if not wave or not exit_event:
        raise ValueError("genuine sentry wave and earned exit frames missing")
    rows=verify((base/"guest-hd-fx-live-witness.txt").read_bytes())
    if not (int(wave.group(1))<rows[0][0]<rows[1][0]<
            int(exit_event.group(1))):
        raise ValueError("HD mode toggles did not occur INSIDE active combat")
    # Require the previously certified after-victory edges as independent
    # controls; two live edges must not replace the V2 late-stage proof.
    preceding=(base/"hd-fx-guest-result.txt").read_text(encoding="ascii")
    if not preceding.startswith("VPD_NEXIUM_HD_FX_GUEST_PASS ") or (
        "guest_simulation_unchanged=yes" not in preceding
    ):
        raise ValueError("post-victory V2 HD mode proof missing")
    inputs=(base/"input-probe.txt").read_text(encoding="ascii").splitlines()
    captures=(base/"visual-probe.txt").read_text(encoding="ascii").splitlines()
    images={}
    for mode in ("off","on"):
        key_line=("host_hd_fx_live_chord_sent=yes keys=D+Z+Q+E "
                  f"expected={mode} guest_seen=yes capture_before_exit=yes")
        if inputs.count(key_line)!=1:
            raise ValueError("real simultaneous Right+Fire+L+R inputs missing")
        label="screen-live-hd-fx-combat-"+mode
        if captures.count("capture="+label)!=1:
            raise ValueError("missing actual pre-exit NeXium X11 screen: "+mode)
        images[mode]=raster(base,label)
    off,off_hash=images["off"]
    on,on_hash=images["on"]
    hud_delta=0
    for y in range(185,245):
        for x in range(945,1240):
            i=(y*1280+x)*3
            if off[i:i+3]!=on[i:i+3]:
                hud_delta+=1
    if hud_delta<10 or off_hash==on_hash:
        raise ValueError("active combat OFF/ON X11 mode presentation unproven")
    result=(
        "VPD_NEXIUM_HD_FX_LIVE_PASS "
        f"wave_frame={int(wave.group(1))} off_frame={rows[0][0]} "
        f"on_frame={rows[1][0]} exit_frame={int(exit_event.group(1))} "
        "real_pad_right_fire_L_R=yes moved_fixed_each=512 "
        "guest_live_edges=2 guest_simulation_unchanged=yes "
        "same_frame_scene_pairs=2 roi_pixels_each=414000 "
        f"live_x11_hud_delta={hud_delta} "
        f"off_ppm_sha256={off_hash} on_ppm_sha256={on_hash} "
        "post_victory_V2_remains_verified=yes source=libnx_pad "
        "original_game_proven=no physical_switch_proven=no\n"
    )
    (base/"hd-fx-live-result.txt").write_text(result,encoding="ascii")
    print(result,end="")
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    args=parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError,UnicodeError,ValueError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"hd-fx-live-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        parser.exit(1,"NeXium live combat HD proof unverified: "+str(exc)+"\n")
