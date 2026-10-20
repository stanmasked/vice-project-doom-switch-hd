#!/usr/bin/env python3
"""Real L+R while the SAME source-owned second-wave bullet is in flight.

Do not confuse host keyboard injection, a HUD label, or a fabricated native
SceneView with independent libnx input and live Simulation evidence.
"""
import argparse
from pathlib import Path
import re
from audit_nexium_fourth_stage import raster
from audit_nexium_hd_hostile_halo import verify as verify_halo
from audit_nexium_fourth_stage import verify as verify_stage

RECORD=re.compile(
    r"^VPD_HD_FX_SENTRY_V1 seq=([12]) mode=(off|on) frame=([0-9]+) "
    r"manual=1 l=1 r=1 edge=1 "
    r"guard_hp=0 wave=1 sentry_hp=2 hero_hp=([1-5]) "
    r"bullet_slot=([0-2]) bullet_age=([0-9]+) "
    r"bullet_x=([0-9]+) bullet_y=([0-9]+) "
    r"bullet_vx=-768 sentry_shots=([0-9]+) stage_clear=0 "
    r"scene_other=([0-9a-f]{16}) scene_displayed=([0-9a-f]{16}) "
    r"roi_pixels=414000 simulation_before=([0-9a-f]{16}) "
    r"simulation_after=([0-9a-f]{16}) "
    r"source=libnx_pad same_frame=yes$"
)

def verify(raw):
    if not isinstance(raw,bytes) or len(raw)>1750 or not raw.endswith(b"\n"):
        raise ValueError("live sentry guest trace missing/truncated/oversized")
    try:
        lines=raw.decode("ascii").splitlines()
    except UnicodeError as error:
        raise ValueError("live sentry guest trace not ASCII") from error
    if len(lines)!=2:
        raise ValueError("exactly two L+R guest edges required during sentry fire")
    results=[]
    for index,line in enumerate(lines):
        match=RECORD.fullmatch(line)
        if not match:
            raise ValueError("invalid source live-sentry HD event")
        (seq,mode,frame,health,slot,age,x,y,shots,
         alternate,displayed,before,after)=match.groups()
        if int(seq)!=index+1 or mode!=("off" if index==0 else "on"):
            raise ValueError("sentry HD transitions not OFF then ON")
        if before!=after or alternate==displayed:
            raise ValueError("sentry HD guest raster mutates physics or lacks pixels")
        event=dict(frame=int(frame),hero_hp=int(health),
                   slot=int(slot),age=int(age),x=int(x),y=int(y),
                   shots=int(shots))
        if (event["frame"]<=0 or event["age"]>=90 or
            event["x"]<=0 or event["x"]>64*16*256 or
            event["y"]<=0 or event["y"]>15*16*256 or
            event["shots"]<1):
            raise ValueError("sentry projectile coordinates/age invalid")
        results.append(event)
    a,b=results
    if (b["frame"]<=a["frame"] or b["age"]<=a["age"] or
        b["age"]-a["age"]!=b["frame"]-a["frame"] or
        a["slot"]!=b["slot"] or a["shots"]!=b["shots"] or
        a["y"]!=b["y"] or a["hero_hp"]!=b["hero_hp"] or
        b["x"]!=a["x"]-768*(b["frame"]-a["frame"])):
        raise ValueError("sentry HD edges do not follow one real moving bullet")
    return results

def audit(evidence):
    base=Path(evidence)
    impact=(base/"fourth-guard-clear-result.txt").read_text("ascii")
    halo=(base/"hd-hostile-halo-result.txt").read_text("ascii")
    if (not impact.startswith("VPD_NEXIUM_FOURTH_GUARD_CLEAR_PASS ") or
        not halo.startswith("VPD_NEXIUM_HOSTILE_HALO_PASS ")):
        raise ValueError("prior authentic guard and halo evidence absent")
    stage=verify_stage(
        (base/"guest-fourth-stage-witness.txt").read_bytes())
    first=verify_halo(
        (base/"guest-hd-hostile-halo-witness.txt").read_bytes())
    witness=base/"guest-hd-fx-sentry-witness.txt"
    if not witness.is_file():
        raise ValueError("real guest sentry shoulder witness absent")
    off,on=verify(witness.read_bytes())
    if (not stage["wave_frame"]<first["frame"]<off["frame"]<
        on["frame"]<stage["exit_frame"] or
        off["shots"]!=first["sentry_shots"] or
        off["slot"]!=first["bullet_slot"]):
        raise ValueError("L+R edges not attributable to first real fourth wave bullet")
    # Native halo witness has bullet age/position from earlier source frame.
    if (off["age"]-first["bullet_age"]!=off["frame"]-first["frame"] or
        off["x"]!=first["bullet_x"]-768*(off["frame"]-first["frame"]) or
        off["y"]!=first["bullet_y"]):
        raise ValueError("sentry HD edges not the first live halo-sampled bullet")
    host=(base/"input-probe.txt").read_text("ascii").splitlines()
    trace=(base/"visual-probe.txt").read_text("ascii").splitlines()
    if host.count("host_sentry_halo_observed=yes source=live_guest")!=1:
        raise ValueError("physical sentry approach lacks source halo gate")
    for mode in ("off","on"):
        if host.count(
            f"host_sentry_fx_chord_sent=yes keys=Q+E expected={mode} guest_seen=yes")!=1:
            raise ValueError("actual sentry L+R host-input witness absent")
        if trace.count(f"capture=screen-live-sentry-hd-fx-{mode}")!=1:
            raise ValueError("native sentry HD X11 screenshot absent")
    rgb_off,sha_off=raster(base,"screen-live-sentry-hd-fx-off")
    rgb_on,sha_on=raster(base,"screen-live-sentry-hd-fx-on")
    changed=0
    for y in range(185,245):
        for x in range(945,1240):
            index=(y*1280+x)*3
            changed+=rgb_off[index:index+3]!=rgb_on[index:index+3]
    if sha_off==sha_on or changed<10:
        raise ValueError("X11 sentry HD status did not change")
    text=("VPD_NEXIUM_HD_FX_SENTRY_PASS "
          f"off_frame={off['frame']} on_frame={on['frame']} "
          f"bullet_slot={off['slot']} bullet_age_off={off['age']} "
          f"bullet_age_on={on['age']} sentry_shots={off['shots']} "
          "real_pad_chords=2 same_live_hostile_bullet=yes "
          "guest_simulation_unchanged=yes roi_pixels=414000 "
          f"status_x11_changed_pixels={changed} "
          f"off_ppm_sha256={sha_off} on_ppm_sha256={sha_on} "
          "source=libnx_pad native_x11_evidence=yes "
          "original_game_proven=no physical_switch_proven=no\n")
    (base/"hd-fx-sentry-result.txt").write_text(text,encoding="ascii")
    print(text,end="")
    return text

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",required=True,type=Path)
    args=parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError,UnicodeError,ValueError) as error:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"hd-fx-sentry-result.txt").write_text(
            "INCONCLUSIVE: "+str(error)+"\n",encoding="ascii")
        parser.exit(1,"Real wave-two pad L+R witness unverified: "+str(error)+"\n")
