#!/usr/bin/env python3
"""Fail closed on false native bullet-halo images or unrelated stage runs."""
import argparse
import importlib.util
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/"tools"/filename)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
fourth=load("fourth_halo_stage","audit_nexium_fourth_stage.py")
FORMAT=re.compile(
    rb"\AVPD_ROMFREE_HOSTILE_HALO_V1 event=fourth_turret_bullet "
    rb"frame=([1-9][0-9]{0,3}) bullet_slot=([0-2]) "
    rb"bullet_x=([1-9][0-9]{0,7}) bullet_y=([1-9][0-9]{0,7}) "
    rb"bullet_age=(0|[1-9][0-9]?) bullet_vx=(-?768) "
    rb"sentry_hp=([12]) sentry_shots=([1-9][0-9]{0,3}) "
    rb"guard_hp=0 wave=1 clear=0 hero_hp=([1-5]) "
    rb"samples=1024 changed=([1-9][0-9]{0,3}) "
    rb"unlit_hash=([0-9a-f]{16}) lit_hash=([0-9a-f]{16}) "
    rb"same_guest_frame=yes native_framebuffer=yes "
    rb"source=live_guest original_game_proven=no\n\Z")
def verify(data):
    if not isinstance(data,bytes) or len(data)>512:
        raise ValueError("guest hostile halo record missing or oversized")
    m=FORMAT.fullmatch(data)
    if not m:
        raise ValueError("invalid native hostile projectile witness")
    keys=("frame","bullet_slot","bullet_x","bullet_y",
          "bullet_age","bullet_vx","sentry_hp","sentry_shots",
          "hero_hp","changed")
    result={k:int(m.group(i+1)) for i,k in enumerate(keys)}
    if (result["frame"]>1200 or result["bullet_age"]>=90 or
        not 3<=result["changed"]<=1024 or
        result["bullet_x"]>64*16*256 or
        result["bullet_y"]>15*16*256 or
        m.group(11)==m.group(12)):
        raise ValueError("native bullet source/pixel evidence out of range")
    result["unlit_hash"]=m.group(11).decode("ascii")
    result["lit_hash"]=m.group(12).decode("ascii")
    return result
def audit(directory):
    base=Path(directory)
    source=base/"guest-hd-hostile-halo-witness.txt"
    if not source.is_file():
        raise ValueError("live guest hostile halo evidence absent")
    state=verify(source.read_bytes())
    stage=base/"guest-fourth-stage-witness.txt"
    if not stage.is_file():
        raise ValueError("independent fourth guest wave/exit evidence absent")
    timeline=fourth.verify(stage.read_bytes())
    if not timeline["wave_frame"]<state["frame"]<timeline["exit_frame"]:
        raise ValueError("hostile projectile observed outside fourth live wave")
    for filename,marker in (
        ("fourth-stage-result.txt","VPD_NEXIUM_FOURTH_STAGE_PASS "),
        ("fourth-retry-result.txt","VPD_NEXIUM_FOURTH_RETRY_PASS "),
        ("hd-footstep-result.txt","VPD_NEXIUM_HD_FOOTSTEP_PASS "),
        ("hd-impact-result.txt","VPD_NEXIUM_HD_HIT_LIGHT_PASS "),
    ):
        file=base/filename
        if not file.is_file() or not file.read_text(
                encoding="ascii").startswith(marker):
            raise ValueError("prior genuine native/X11 stage evidence absent: "+filename)
    screen=base/"screen-live-fourth-stage-clear.png"
    if not screen.is_file() or not screen.read_bytes().startswith(
            b"\x89PNG\r\n\x1a\n"):
        raise ValueError("real fourth-stage X11 image missing")
    output=(
        "VPD_NEXIUM_HOSTILE_HALO_PASS "
        f"frame={state['frame']} bullet_slot={state['bullet_slot']} "
        f"bullet_age={state['bullet_age']} "
        f"changed_halo_pixels={state['changed']} "
        f"unlit_hash={state['unlit_hash']} lit_hash={state['lit_hash']} "
        "same_native_guest_frame=yes real_active_enemy_bullet=yes "
        "fourth_wave_pad_control=yes independent_x11_stage=yes "
        "source=live_guest original_game_proven=no "
        "physical_switch_proven=no\n")
    (base/"hd-hostile-halo-result.txt").write_text(output,encoding="ascii")
    print(output,end="")
    return state
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",type=Path,required=True)
    args=p.parse_args()
    try:
        audit(args.evidence)
    except (ValueError,UnicodeError,OSError) as error:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"hd-hostile-halo-result.txt").write_text(
            "INCONCLUSIVE: "+str(error)+"\n",encoding="ascii")
        p.exit(1,"Hostile halo native guest proof unverified: "+str(error)+"\n")
