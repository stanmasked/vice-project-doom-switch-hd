#!/usr/bin/env python3
"""Fail-closed NeXium proof of genuine guest L+R HD-effects mode edges."""
import argparse
import hashlib
from pathlib import Path
import re

from audit_nexium_fourth_stage import raster

RECORD=re.compile(
    r"^VPD_HD_FX_GUEST_V2 seq=([12]) mode=(off|on) frame=([0-9]+) "
    r"manual=1 l=1 r=1 edge=1 scene_other=([0-9a-f]{16}) "
    r"scene_displayed=([0-9a-f]{16}) roi_pixels=414000 "
    r"simulation_before=([0-9a-f]{16}) simulation_after=([0-9a-f]{16}) "
    r"source=libnx_pad same_frame=yes$"
)

def verify(raw):
    if not isinstance(raw,bytes) or len(raw)>900 or not raw.endswith(b"\n"):
        raise ValueError("HD FX guest witness missing, oversized or truncated")
    try:
        text=raw.decode("ascii")
    except UnicodeError as e:
        raise ValueError("HD FX witness must be ASCII") from e
    rows=text.splitlines()
    if len(rows)!=2:
        raise ValueError("exactly two native shoulder edges required")
    parsed=[]
    for index,row in enumerate(rows):
        m=RECORD.fullmatch(row)
        if not m:
            raise ValueError("malformed native shoulder edge")
        seq,mode,frame,other,displayed,simulation_before,simulation_after=m.groups()
        if int(seq)!=index+1 or mode!=("off" if index==0 else "on"):
            raise ValueError("HD FX state transition order violated")
        if int(frame)<=0 or other==displayed:
            raise ValueError("guest frame or effect-only pixels not proven")
        if simulation_before!=simulation_after:
            raise ValueError("HD FX guest raster modified simulation state")
        parsed.append((int(frame),other,displayed,simulation_before))
    if parsed[1][0]<=parsed[0][0]:
        raise ValueError("second shoulder edge must follow the first")
    return parsed

def audit(base):
    base=Path(base)
    previous=base/"fourth-stage-result.txt"
    if not previous.is_file() or not previous.read_text("ascii").startswith(
        "VPD_NEXIUM_FOURTH_STAGE_PASS "
    ):
        raise ValueError("fourth manual stage success missing")
    prior=re.search(r"\bexit_frame=(\d+)\b",previous.read_text("ascii"))
    if not prior:
        raise ValueError("fourth stage exit frame unavailable")
    proof=base/"guest-hd-fx-toggle-witness.txt"
    if not proof.is_file():
        raise ValueError("actual NeXium SD shoulder trace absent")
    rows=verify(proof.read_bytes())
    if rows[0][0]<=int(prior.group(1)):
        raise ValueError("HD FX edge predates completed fourth stage")
    inputs=(base/"input-probe.txt").read_text("ascii").splitlines()
    for mode in ("off","on"):
        expected=f"host_hd_fx_chord_sent=yes keys=Q+E expected={mode} guest_seen=yes"
        if inputs.count(expected)!=1:
            raise ValueError("real host shoulder input missing: "+mode)
    captures=(base/"visual-probe.txt").read_text("ascii").splitlines()
    for mode in ("off","on"):
        if captures.count("capture=screen-live-hd-fx-"+mode)!=1:
            raise ValueError("real X11 screenshot missing: "+mode)
    off,off_hash=raster(base,"screen-live-hd-fx-off")
    on,on_hash=raster(base,"screen-live-hd-fx-on")
    # Only the real X11 raster is compared, not a generated test image.
    # Pixel evidence in the guest file EXCLUDES this HUD area, so neither
    # the screenshot nor the text alone can counterfeit scene-effects proof.
    difference=0
    for y in range(185,245):
        for x in range(945,1240):
            offset=(y*1280+x)*3
            if off[offset:offset+3]!=on[offset:offset+3]:
                difference+=1
    if difference<10 or off_hash==on_hash:
        raise ValueError("X11 HUD did not reflect two native shoulder modes")
    result=(
        "VPD_NEXIUM_HD_FX_GUEST_PASS "
        f"off_frame={rows[0][0]} on_frame={rows[1][0]} "
        "pad_chords=2 guest_edges=2 same_frame_visual_pairs=2 "
        "guest_simulation_unchanged=yes scene_roi_pixels=414000 "
        "status_x11_changed_pixels="
        f"{difference} off_ppm_sha256={off_hash} on_ppm_sha256={on_hash} "
        "source=libnx_pad native_x11_evidence=yes "
        "original_game_proven=no physical_switch_proven=no\n"
    )
    (base/"hd-fx-guest-result.txt").write_text(result,encoding="ascii")
    print(result,end="")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",required=True,type=Path)
    a=p.parse_args()
    try:
        audit(a.evidence)
    except (OSError,ValueError,UnicodeError) as exc:
        a.evidence.mkdir(parents=True,exist_ok=True)
        (a.evidence/"hd-fx-guest-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        p.exit(1,"NeXium HD FX shoulder proof unverified: "+str(exc)+"\n")
