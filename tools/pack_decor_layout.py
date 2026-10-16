#!/usr/bin/env python3
"""Strict JSON -> VLAY v1 decor placements and optional C++ default header.

Fully independently authored diagnostic positions. No NES game data.
"""
import argparse
import json
import struct
import zlib
from pathlib import Path

KINDS={"beacon":0,"fan":1}
LAYERS={"rear":0,"front":1}

def _int(value,low,high,name):
    if type(value) is not int or not low<=value<=high:
        raise ValueError(f"{name} out of range")
    return value

def validate(data):
    if not isinstance(data,dict) or set(data)!={"schema","objects"}:
        raise ValueError("Expected exactly schema and objects")
    if type(data["schema"]) is not int or data["schema"]!=1:
        raise ValueError("Unsupported layout schema")
    objects=data["objects"]
    if not isinstance(objects,list) or len(objects)>64:
        raise ValueError("At most 64 decoration objects")
    rows=[]
    for idx,item in enumerate(objects):
        if not isinstance(item,dict) or set(item)!={
            "x","y","kind","layer","first_frame","frames","period_ticks","phase_frames"
        }:
            raise ValueError(f"Invalid object {idx} property set")
        kind=KINDS.get(item["kind"]) if isinstance(item["kind"],str) else None
        layer=LAYERS.get(item["layer"]) if isinstance(item["layer"],str) else None
        if kind is None or layer is None:
            raise ValueError(f"Invalid kind/layer for object {idx}")
        x=_int(item["x"],-16384,16384,"world x")
        y=_int(item["y"],-1024,1024,"world y")
        first=_int(item["first_frame"],0,3,"first frame")
        length=_int(item["frames"],1,4,"frame count")
        if first+length>4:
            raise ValueError("Animation frames must fit four-frame atlas")
        period=_int(item["period_ticks"],1,600,"period ticks")
        phase=_int(item["phase_frames"],0,65535,"phase frames")
        rows.append((x,y,kind,layer,first,length,period,phase))
    return rows

def pack(data):
    rows=validate(data)
    payload=b"".join(struct.pack("<hhBBBBHH",*row) for row in rows)
    header=b"VLAY"+struct.pack("<4H",1,len(rows),12,0)
    return header+struct.pack("<I",zlib.crc32(payload)&0xffffffff)+payload

def generate_cpp(data):
    rows=validate(data)
    if not rows:
        raise ValueError("Generated compile-time default must have at least one object")
    records=["    {"+", ".join(str(x) for x in row)+"}," for row in rows]
    return ("#pragma once\n#include \"decor_layout.hpp\"\nnamespace vpd_layout {\n"
            "inline constexpr vpd::DecorPlacement kPlacements[] = {\n"
            +"\n".join(records)+"\n};\n"
            f"inline constexpr vpd::DecorLayout kLayout{{kPlacements, {len(rows)}}};\n"
            "}\n")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("json",type=Path)
    p.add_argument("--binary",type=Path)
    p.add_argument("--header",type=Path)
    args=p.parse_args()
    if not args.binary and not args.header:
        p.error("Request --binary and/or --header")
    data=json.loads(args.json.read_text(encoding="utf8"))
    if args.binary:
        args.binary.parent.mkdir(parents=True,exist_ok=True)
        args.binary.write_bytes(pack(data))
    if args.header:
        args.header.parent.mkdir(parents=True,exist_ok=True)
        args.header.write_text(generate_cpp(data),encoding="utf8")
    print(f"VLAY v1: {len(validate(data))} authored world props")

if __name__=="__main__":
    main()
