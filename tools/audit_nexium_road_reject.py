#!/usr/bin/env python3
"""Check real NeXium corrupted numeric SD fail-closed, with Y fallback."""
from __future__ import annotations
import argparse
from pathlib import Path
from audit_nexium_driving_live import p6_payload
from audit_nexium_road_x11_shape import ROWS,detect_strip
from generate_corrupt_synthetic_road_bundle import corrupt

def single(path:Path,prefix:str)->dict[str,str]:
    rows=path.read_text("ascii").splitlines()
    if len(rows)!=1:raise ValueError("need exactly one native guest rejection")
    words=rows[0].split()
    if words[0]!=prefix:raise ValueError("guest proof marker mismatch")
    out={}
    for word in words[1:]:
        k,eq,v=word.partition("=")
        if not eq or not v or k in out:raise ValueError("invalid guest evidence")
        out[k]=v
    return out

def audit(folder:Path,broken:bytes,kind:str)->None:
    if broken!=corrupt(kind):
        raise ValueError("source free corrupt SD input not identical to generated fixture")
    state=single(folder/"guest-private-road-sd-startup.txt",
                 "VPD_PRIVATE_ROAD_SD_V1")
    if state!={"mounted":"1","loaded":"0","samples":"0",
              "first_frame":"0","last_frame":"0",
              "source":"nro_startup","original_art":"no",
              "camera_collision_proven":"no"}:
        raise ValueError("real guest accepted corrupted SD file")
    reject=single(folder/"guest-private-road-reject-witness.txt",
                  "VPD_PRIVATE_ROAD_REJECT_V1")
    for k,v in {"loaded":"0","native_r3":"1","private_active":"0",
                "road_pixel":"ff42322a","shoulder_pixel":"ff4c503d",
                "source":"libnx_live_raster","original_art":"no",
                "collision_proven":"no"}.items():
        if reject.get(k)!=v:raise ValueError("R3 rejection not source-owned")
    required={"loaded","native_r3","private_active","frame","health",
              "road_pixel","shoulder_pixel","car_pixel","hud_pixel",
              "platform_fp","source","original_art","collision_proven"}
    if set(reject)!=required:raise ValueError("private path/raw leakage in proof")
    if not 0<=int(reject["health"])<=5 or int(reject["frame"])<=0:
        raise ValueError("R3 did not run on an active game frame")
    if len(reject["platform_fp"])!=16:
        raise ValueError("no full platform simulation fingerprint")
    fallbacks=(folder/"guest-original-seven-fallback.txt").read_text("ascii").splitlines()
    if len(fallbacks)!=1 or not fallbacks[0].startswith(
         "VPD_ROAD_REVIEW_V1 seq=1 original_frame=600 "):
        raise ValueError("missing authentic Y fallback within same NRO")
    off=p6_payload(folder/"screen-corrupt-r3-off.ppm")
    built=p6_payload(folder/"screen-corrupt-y-reference.ppm")
    for row in ROWS:
        if detect_strip(off,row) is not None:
            raise ValueError("invalid SD still rendered private X11 sample")
        if detect_strip(built,row) is None:
            raise ValueError("valid seven-frame Y source reference missing on X11")
    print("VPD_NEXIUM_CORRUPT_ROAD_SD_REJECT_PASS"
          f" variant={kind} actual_r3_guest_rejected=yes"
          " native_y_fallback=yes no_private_swatch_x11=yes"
          " original_source_assets=no")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--kind",required=True,
                   choices=("bad_crc","bad_anchor","truncated"))
    args=p.parse_args()
    audit(args.evidence,args.input.read_bytes(),args.kind)
