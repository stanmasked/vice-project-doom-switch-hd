#!/usr/bin/env python3
"""Strict independent ROM-free NeXium driving stage-blackout auditor."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
from audit_nexium_driving_live import p6_payload

SCENES=("last_road",)+("black",)*41+("platform",)
KEYS={"seq","scene","road_frame","black_frames","black_pixel",
      "platform_before","platform_after","source","original_stage_clear_proven"}

def verify_records(lines: list[str]) -> None:
    if len(lines)!=43:
        raise ValueError("expected last road, 41 black and platform (43 records)")
    origin=None
    baseline=None
    for n,(line,scene) in enumerate(zip(lines,SCENES)):
        parts=line.split()
        if not parts or parts[0]!="VPD_DRIVING_EXIT_V1":
            raise ValueError("not a native transition witness")
        d={}
        for part in parts[1:]:
            k,sep,v=part.partition("=")
            if not sep or not k or not v or k in d:
                raise ValueError("malformed transition witness")
            d[k]=v
        if set(d)!=KEYS or d["scene"]!=scene or int(d["seq"])!=n:
            raise ValueError("scene sequence altered")
        if d["source"]!="libnx_frame" or d["original_stage_clear_proven"]!="0":
            raise ValueError("not a source-driven synthetic scene record")
        should_black=n if n<=41 else 41
        if int(d["black_frames"])!=should_black:
            raise ValueError("missing or repeated black presentation")
        if d["black_pixel"]!=("1" if scene=="black" else "0"):
            raise ValueError("nonblack pixel in blackout guest scene")
        if len(d["platform_before"])!=16 or d["platform_before"]!=d["platform_after"]:
            raise ValueError("platform changed during transition")
        int(d["platform_before"],16)
        if baseline is None:baseline=d["platform_before"]
        if d["platform_before"]!=baseline:
            raise ValueError("platform fingerprint diverged")
        frame=int(d["road_frame"])
        if frame<0:
            raise ValueError("invalid road origin")
        if origin is None:origin=frame
        if frame!=origin:
            raise ValueError("not the same final road frame")

def audit(folder: Path) -> None:
    verify_records((folder/"guest-driving-exit-witness.txt").read_text("ascii").splitlines())
    images=[p6_payload(folder/(name+".ppm")) for name in
            ("screen-exit-road","screen-exit-black","screen-exit-platform")]
    if len(set(hashlib.sha256(p).digest() for p in images))!=3:
        raise ValueError("three real X11 scenes must be different")
    black=images[1]
    near_black=total=0
    for y in range(170,550,12):
        for x in range(350,930,12):
            pixel=black[3*(y*1280+x):3*(y*1280+x)+3]
            total+=1
            near_black+=int(len(pixel)==3 and max(pixel)<28)
    if near_black*100<80*total:
        raise ValueError("blackout not visible in central X11 viewport")
    print("VPD_NEXIUM_DRIVING_BLACKOUT_PASS"
          " guest_black_frames=41 native_records=43"
          " x11_three_scenes=yes platform_unchanged=yes"
          " original_stage_completion_proven=no")

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",type=Path,required=True)
    audit(p.parse_args().evidence)
if __name__=="__main__":main()
