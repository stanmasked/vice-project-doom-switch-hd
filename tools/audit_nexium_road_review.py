#!/usr/bin/env python3
"""Independent source-owned NeXium exact road-reference swatch auditor."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
from audit_nexium_driving_live import p6_payload

ORIGINAL=[
    (600,66,188),(744,66,188),(760,82,173),
    (784,98,156),(800,100,155),(840,84,171),(920,116,203),(0,0,0)
]
KEYS={
    "seq","original_frame","drive_frame","left_hd","right_hd",
    "outside_left","edge_left","edge_right","outside_right",
    "off_pixel","car_pixel","hud_pixel","health","flash",
    "platform_fp","source","source_art","collision_proven"
}
COLOR_PANEL=0xff22180e
COLOR_EDGE=0xff75bee9
COLOR_OFF=0xff4c503d
COLOR_HUD5=0xff5b55d3
COLOR_HUD_LESS=0xff271911
COLOR_CAR=0xff3f2fa3
COLOR_FLASH=0xff7ec8e8

def decode(raw: str) -> dict[str,str]:
    words=raw.split()
    if not words or words[0]!="VPD_ROAD_REVIEW_V1":
        raise ValueError("missing original-frame raster witness prefix")
    d={}
    for word in words[1:]:
        k,sep,v=word.partition("=")
        if not sep or not k or not v or k in d:
            raise ValueError("duplicated/malformed guest road-review field")
        d[k]=v
    if set(d)!=KEYS:
        raise ValueError("unexpected witness fields")
    return d

def hex32(value: str) -> int:
    if len(value)!=8 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("invalid RGB framebuffer sample")
    return int(value,16)

def validate(records: list[str]) -> None:
    if len(records)!=8:
        raise ValueError("eight genuine sequential native review records needed")
    last_frame=-1
    last_fp=None
    for i,(line,(frame,left,right)) in enumerate(zip(records,ORIGINAL),start=1):
        d=decode(line)
        if (int(d["seq"])!=i or int(d["original_frame"])!=frame or
            d["source"]!="libnx_drawScene" or
            d["source_art"]!="none" or d["collision_proven"]!="0"):
            raise ValueError("wrong original numerical sample order/provenance")
        df=int(d["drive_frame"])
        if df<=last_frame:
            raise ValueError("review gesture was not a fresh native frame")
        last_frame=df
        fp=d["platform_fp"]
        if len(fp)!=16 or any(c not in "0123456789abcdef" for c in fp):
            raise ValueError("malformed independent platform fingerprint")
        if last_fp is not None and last_fp!=fp:
            raise ValueError("platform simulation changed during road review")
        last_fp=fp
        health=int(d["health"])
        flash=int(d["flash"])
        if not 0<=health<=5 or flash not in (0,1):
            raise ValueError("car source status not plausible")
        if (hex32(d["car_pixel"])!=(COLOR_FLASH if flash else COLOR_CAR) or
            hex32(d["hud_pixel"])!=(COLOR_HUD5 if health==5 else COLOR_HUD_LESS)):
            raise ValueError("car/HUD not sourced from same native frame")
        if i<8:
            if (int(d["left_hd"])!=left*5 or
                int(d["right_hd"])!=(right+1)*5-1):
                raise ValueError("measured source RGB interval mismatched HD pixels")
            for prop,expected in (
                ("outside_left",COLOR_PANEL),("outside_right",COLOR_PANEL),
                ("edge_left",COLOR_EDGE),("edge_right",COLOR_EDGE)):
                if hex32(d[prop])!=expected:
                    raise ValueError("actual source framebuffer swatch pixel mismatch")
            if hex32(d["off_pixel"])!=0:
                raise ValueError("active image review improperly emitted OFF value")
        else:
            if int(d["left_hd"])!=0 or int(d["right_hd"])!=0:
                raise ValueError("selector failed to reach OFF")
            if hex32(d["off_pixel"])!=COLOR_OFF:
                raise ValueError("road image overlay remained after OFF gesture")
            for prop in ("outside_left","edge_left","edge_right","outside_right"):
                if hex32(d[prop])!=0:
                    raise ValueError("OFF selector still has interval pixel samples")

def audit(folder: Path) -> None:
    validate((folder/"guest-road-review-witness.txt").read_text("ascii").splitlines())
    images=[p6_payload(folder/("screen-review-"+str(i)+".ppm")) for i in (1,5,8)]
    if len({hashlib.sha256(p).digest() for p in images})!=3:
        raise ValueError("review source images at 600/800/OFF indistinguishable")
    print("VPD_NEXIUM_ROAD_REVIEW_PASS guest_swatches=7"
          " guest_off=1 original_numeric_x_intervals=yes"
          " car_hud_intact=yes platform_unchanged=yes"
          " original_source_art=no original_road_physics_proven=no")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",type=Path,required=True)
    audit(p.parse_args().evidence)
