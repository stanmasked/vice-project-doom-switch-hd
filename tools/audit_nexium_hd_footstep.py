#!/usr/bin/env python3
"""Fail closed unless a real fourth-run right step changes native dust pixels."""
import argparse
import importlib.util
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "fourth_retry_provenance",ROOT/"tools/audit_nexium_fourth_retry.py")
fourth=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fourth)
SCHEMA=re.compile(
    rb"\AVPD_ROMFREE_HD_FOOTSTEP_V1 event=fourth_ground_move "
    rb"frame=([1-9][0-9]{0,2}) hero_x=([1-9][0-9]{0,7}) "
    rb"hero_vx=512 grounded=1 hero_hp=5 guard_hp=3 "
    rb"shots=0 wave=0 clear=0 "
    rb"samples=1056 changed=([1-9][0-9]{0,3}) "
    rb"no_dust_hash=([0-9a-f]{16}) dust_hash=([0-9a-f]{16}) "
    rb"same_guest_frame=yes native_framebuffer=yes "
    rb"source=live_guest original_game_proven=no\n\Z")
def verify(raw):
    if not isinstance(raw,bytes) or len(raw)>440:
        raise ValueError("native footstep evidence missing or oversized")
    match=SCHEMA.fullmatch(raw)
    if not match:
        raise ValueError("malformed native footstep proof")
    frame=int(match.group(1))
    x=int(match.group(2))
    changed=int(match.group(3))
    if (not 8<=frame<=100 or
        not (3*16+16)*256<=x<=(3*16+120)*256 or
        not 3<=changed<=1056 or match.group(4)==match.group(5)):
        raise ValueError("footstep evidence outside genuine moving-hero envelope")
    return {"frame":frame,"x":x,"changed":changed,
            "no_dust_hash":match.group(4).decode("ascii"),
            "dust_hash":match.group(5).decode("ascii")}
def audit(evidence):
    base=Path(evidence)
    witness=base/"guest-hd-footstep-witness.txt"
    if not witness.is_file():
        raise ValueError("same-frame native footstep witness absent")
    trace=verify(witness.read_bytes())
    source=base/"guest-fourth-retry-witness.txt"
    if not source.is_file():
        raise ValueError("actual fourth-run guest reset and right move absent")
    fourth_move=fourth.verify(source.read_bytes())
    if trace["frame"]!=fourth_move["frame"] or trace["x"]!=fourth_move["after_x"]:
        raise ValueError("dust pixel evidence is not the actual fourth right-move frame")
    prior=base/"fourth-retry-result.txt"
    if not prior.is_file() or not prior.read_text(
        encoding="ascii").startswith("VPD_NEXIUM_FOURTH_RETRY_PASS "):
        raise ValueError("prior physical Minus/Right and X11 PASS missing")
    visual=base/"visual-probe.txt"
    if not visual.is_file() or not all(
            marker in visual.read_text(encoding="ascii").splitlines()
            for marker in ("capture=screen-live-fourth-move",
                           "live_fourth_movement_raster_after_guest_event=yes")):
        raise ValueError("fourth right-move X11 screenshots not confirmed")
    for ext in ("png","ppm"):
        p=base/("screen-live-fourth-move."+ext)
        if not p.is_file():
            raise ValueError("no real fourth-move X11 image "+ext)
        if ext=="png" and not p.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("fourth right-move PNG signature absent")
    message=(
        "VPD_NEXIUM_HD_FOOTSTEP_PASS "
        f"frame={trace['frame']} hero_x={trace['x']} "
        f"changed_heel_pixels={trace['changed']} "
        f"without_dust_hash={trace['no_dust_hash']} "
        f"with_dust_hash={trace['dust_hash']} "
        "same_native_guest_frame=yes physical_right_input=yes "
        "native_x11_evidence=yes source=live_guest "
        "original_game_proven=no physical_switch_proven=no\n")
    (base/"hd-footstep-result.txt").write_text(message,encoding="ascii")
    print(message,end="")
    return trace
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",type=Path,required=True)
    args=p.parse_args()
    try:
        audit(args.evidence)
    except (OSError,ValueError,UnicodeError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"hd-footstep-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        p.exit(1,"NeXium native footstep proof missing: "+str(exc)+"\n")
