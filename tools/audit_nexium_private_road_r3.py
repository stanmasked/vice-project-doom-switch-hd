#!/usr/bin/env python3
"""Validate real source-owned 37 R3+OFF NeXium guest records and host X11.

Source numeric content is GENERATED from invented non-anchor intervals
and seven already published original RGB-observation anchors. The owner's
private full 37-frame JSON and NES art are neither read nor uploaded.
"""
from __future__ import annotations
import argparse
import hashlib
import struct
import zlib
from pathlib import Path
from audit_nexium_driving_live import p6_payload
from audit_nexium_road_x11_shape import detect_strip,ROWS
from generate_synthetic_road_bundle import synthetic_bundle

PREFIX="VPD_PRIVATE_ROAD_R3_V1"
KEYS={"seq","source_frame","drive_frame","left_hd","right_hd",
      "outside_left","edge_left","edge_right","outside_right",
      "marker_pixel","off_pixel","car_pixel","hud_pixel","health",
      "flash","platform_fp","source","original_art",
      "camera_collision_proven"}
PANEL="ff22180e"
EDGE="ff75bee9"
OFF="ff4c503d"
CAR="ff3f2fa3"
FLASH="ff7ec8e8"
HUD5="ff5b55d3"
HUDLESS="ff271911"

def source_rows(raw:bytes)->list[tuple[int,int,int]]:
    if raw!=synthetic_bundle():
        raise ValueError("not the expected completely source-free CI bundle")
    if len(raw)!=164:
        raise ValueError("malformed synthetic packet size")
    magic,ver,count,checksum=struct.unpack_from("<8sHHI",raw)
    if (magic,ver,count)!=(b"VPDROAD1",1,37) or (
            checksum!=zlib.crc32(raw[16:])):
        raise ValueError("binary packet CRC/header failed")
    return list(struct.iter_unpack("<HBB",raw[16:]))

def _decode(raw:str)->dict[str,str]:
    words=raw.split()
    if not words or words[0]!=PREFIX:
        raise ValueError("missing actual R3 native framebuffer label")
    result={}
    for word in words[1:]:
        k,eq,v=word.partition("=")
        if not eq or not v or k in result:
            raise ValueError("malformed source-owned guest event")
        result[k]=v
    if set(result)!=KEYS:
        raise ValueError("unexpected native private R3 witness fields")
    return result

def _hex(s:str)->int:
    if len(s)!=8 or any(c not in "0123456789abcdef" for c in s):
        raise ValueError("invalid source pixel hex")
    return int(s,16)

def validate_records(lines:list[str],bundle:bytes)->None:
    records=source_rows(bundle)
    if len(lines)!=38:
        raise ValueError("need 37 exact samples and one OFF guest record")
    first_platform=None
    prior_native=0
    for seq,line in enumerate(lines,1):
        item=_decode(line)
        sample=records[seq-1] if seq<=37 else None
        frame,left,right=sample if sample else (0,0,0)
        if (int(item["seq"])!=seq or
            int(item["source_frame"])!=frame or
            item["source"]!="libnx_framebuffer" or
            item["original_art"]!="none" or
            item["camera_collision_proven"]!="no"):
            raise ValueError("R3 selector order or provenance mismatch")
        native=int(item["drive_frame"])
        if native<=prior_native:raise ValueError("stale or replayed guest frame")
        prior_native=native
        fp=item["platform_fp"]
        if len(fp)!=16 or any(c not in "0123456789abcdef" for c in fp):
            raise ValueError("bad frozen platform fingerprint")
        if first_platform is None:first_platform=fp
        elif fp!=first_platform:raise ValueError("platform game changed")
        health=int(item["health"])
        flash=int(item["flash"])
        if not 0<=health<=5 or flash not in (0,1):
            raise ValueError("invalid independent car state")
        if (_hex(item["car_pixel"])!=int(FLASH if flash else CAR,16)
            or _hex(item["hud_pixel"])!=int(HUD5 if health==5 else HUDLESS,16)):
            raise ValueError("guest player-car/HUD pixels changed")
        if sample:
            if (int(item["left_hd"]),int(item["right_hd"]))!=(
                left*5,(right+1)*5-1):
                raise ValueError("loaded numeric interval not rendered at 5x")
            for k,value in (("outside_left",PANEL),
                            ("outside_right",PANEL),("edge_left",EDGE),
                            ("edge_right",EDGE),("marker_pixel",EDGE)):
                if _hex(item[k])!=int(value,16):
                    raise ValueError("guest private visual pixel wrong")
            if _hex(item["off_pixel"])!=0:
                raise ValueError("OFF-only pixel recorded during review")
        else:
            if (int(item["left_hd"]) or int(item["right_hd"]) or
                _hex(item["off_pixel"])!=int(OFF,16)):
                raise ValueError("R3 did not reset to normal road after #38")
            for k in ("outside_left","outside_right","edge_left",
                      "edge_right","marker_pixel"):
                if _hex(item[k])!=0:
                    raise ValueError("stale swatch details on OFF guest record")

def validate_host_screens(folder:Path,bundle:bytes)->None:
    source=source_rows(bundle)
    indices=[1,22,37,38]
    images=[p6_payload(folder/f"screen-r3-{i}.ppm") for i in indices]
    if len({hashlib.sha256(im).digest() for im in images})!=4:
        raise ValueError("genuine host screenshots not distinct")
    strips=[]
    for seq,img in zip(indices,images):
        found=[detect_strip(img,y) for y in ROWS]
        if seq==38:
            if any(s is not None for s in found):
                raise ValueError("OFF still has private RGB fill in X11")
            continue
        if any(s is None for s in found) or len(set(found))!=1:
            raise ValueError("private R3 swatch not visible on real X11")
        strips.append(found[0])
    wide,narrow,shift=strips
    fw,fl,fr=source[0]
    nw,nl,nr=source[21]
    lw,ll,lr=source[-1]
    if (fw,nw,lw)!=(600,800,920):
        raise ValueError("wrong observed sample labels")
    nominal=[(r-l+1)*5-10 for _,l,r in (source[0],source[21],source[-1])]
    display_scale=wide.width/nominal[0]
    if not 0.8<=display_scale<=1.10:
        raise ValueError("NeXium screen scale unexpectedly changed")
    for s,expected in zip(strips,nominal):
        if abs(s.width-expected*display_scale)>9:
            raise ValueError("X11 width contradicts private numeric bundle")
    predicted=((ll+lr)-(fl+fr))*2.5*display_scale
    actual=((shift.first+shift.last)-(wide.first+wide.last))/2
    if abs(actual-predicted)>14:
        raise ValueError("late source-image lateral shift missing on X11")
    if not wide.width>shift.width>narrow.width:
        raise ValueError("road narrowing/widening order lost")

def audit(folder:Path,bundle:bytes)->None:
    validate_records((folder/"guest-private-road-r3-witness.txt"
                      ).read_text("ascii").splitlines(),bundle)
    validate_host_screens(folder,bundle)
    print("VPD_NEXIUM_PRIVATE_ROAD_R3_PASS"
          " native_pad_edges=38 guest_numeric_samples=37 guest_off=1"
          " host_x11_samples=4"
          " source=synthetic_bundle"
          " original_game_camera_proven=no original_assets=no")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",required=True,type=Path)
    p.add_argument("--input",required=True,type=Path)
    args=p.parse_args()
    audit(args.evidence,args.input.read_bytes())
