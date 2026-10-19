#!/usr/bin/env python3
"""Strict actual-NRO lit/unlit framebuffer sample audit at a real fourth hit."""
import argparse
import importlib.util
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "real_fourth_combat",ROOT/"tools/audit_nexium_fourth_combat.py")
combat_audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(combat_audit)
FORMAT=re.compile(
    rb"\AVPD_ROMFREE_HD_HIT_LIGHT_V1 "
    rb"event=source_guard_impact frame=([1-9][0-9]{0,3}) "
    rb"guard_hp=2 guard_hits=1 guard_flash=([1-9][0-9]?) "
    rb"hero_hp=5 shots=1 sentry_hp=2 wave=0 clear=0 "
    rb"samples=25 changed=([1-9][0-9]?) "
    rb"unlit_hash=([0-9a-f]{16}) lit_hash=([0-9a-f]{16}) "
    rb"same_simulation_frame=yes native_framebuffer=yes "
    rb"source=live_guest original_game_proven=no\n\Z")

def verify(raw):
    if not isinstance(raw,bytes) or len(raw)>420:
        raise ValueError("native framebuffer witness malformed/oversized")
    match=FORMAT.fullmatch(raw)
    if not match:
        raise ValueError("missing canonical guest hit-light event")
    frame,flash,changed=(int(match.group(i)) for i in (1,2,3))
    if flash>12 or changed<3 or changed>25 or match.group(4)==match.group(5):
        raise ValueError("invalid real hit strength or unchanged pixels")
    return {"frame":frame,"flash":flash,"changed":changed,
            "unlit_hash":match.group(4).decode("ascii"),
            "lit_hash":match.group(5).decode("ascii")}

def audit(directory):
    path=Path(directory)
    witness=path/"guest-hd-hit-light-witness.txt"
    if not witness.is_file():
        raise ValueError("HD light guest framebuffer proof absent")
    sample=verify(witness.read_bytes())
    original=path/"guest-fourth-combat-witness.txt"
    if not original.is_file():
        raise ValueError("corresponding physical fourth-run Fire evidence absent")
    fire=combat_audit.verify(original.read_bytes())
    if not fire["hit_frame"]<=sample["frame"]<fire["hit_frame"]+12:
        raise ValueError("HD sample cannot be linked to authentic guard impact")
    previous=path/"fourth-combat-result.txt"
    if not previous.is_file() or not previous.read_text(
            encoding="ascii").startswith("VPD_NEXIUM_FOURTH_COMBAT_PASS "):
        raise ValueError("physical X11 fourth-run hit was not proven")
    for name in ("screen-live-fourth-impact.png",
                 "screen-live-fourth-impact.ppm"):
        if not (path/name).is_file():
            raise ValueError("matching genuine X11 framebuffer screenshot absent")
    result=(
        "VPD_NEXIUM_HD_HIT_LIGHT_PASS "
        f"frame={sample['frame']} guard_flash={sample['flash']} "
        f"changed_guard_samples={sample['changed']} "
        f"unlit_hash={sample['unlit_hash']} "
        f"lit_hash={sample['lit_hash']} "
        "same_native_guest_frame=yes real_guard_impact=yes "
        "prior_real_x11_hit=yes source=live_guest "
        "original_game_proven=no physical_switch_proven=no\n")
    (path/"hd-hit-light-result.txt").write_text(result,encoding="ascii")
    print(result,end="")
    return sample

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",type=Path,required=True)
    args=p.parse_args()
    try:
        audit(args.evidence)
    except (ValueError,OSError,UnicodeError) as err:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"hd-hit-light-result.txt").write_text(
            "INCONCLUSIVE: "+str(err)+"\n",encoding="ascii")
        p.exit(1,"Guest native impact-light proof not verified: "+str(err)+"\n")
