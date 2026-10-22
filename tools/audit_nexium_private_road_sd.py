#!/usr/bin/env python3
"""Independently audit NeXium guest startup with an invented numeric SD file."""
from __future__ import annotations
import argparse
from pathlib import Path
import struct
import zlib
from generate_synthetic_road_bundle import synthetic_bundle

EXPECTED={
    "mounted":"1","loaded":"1","samples":"37",
    "first_frame":"600","last_frame":"920",
    "source":"nro_startup","original_art":"no",
    "camera_collision_proven":"no",
}
def validate(raw:str,bundle:bytes)->None:
    lines=raw.splitlines()
    if len(lines)!=1:raise ValueError("expected one guest startup record")
    words=lines[0].split()
    if words[0]!="VPD_PRIVATE_ROAD_SD_V1":
        raise ValueError("not a guest native startup witness")
    fields={}
    for word in words[1:]:
        k,eq,v=word.partition("=")
        if not eq or not v or k in fields:raise ValueError("bad guest fields")
        fields[k]=v
    if fields!=EXPECTED:raise ValueError("private SD was not loaded by guest")
    if bundle!=synthetic_bundle():raise ValueError("not deterministic original-free SD")
    if len(bundle)!=164:raise ValueError("private SD file size mismatched")
    magic,version,count,crc=struct.unpack("<8sHHI",bundle[:16])
    if (magic,version,count)!=(b"VPDROAD1",1,37) or crc!=zlib.crc32(bundle[16:]):
        raise ValueError("private SD reference header invalid")

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--input",type=Path,required=True)
    args=p.parse_args()
    validate((args.evidence/"guest-private-road-sd-startup.txt").read_text("ascii"),
             args.input.read_bytes())
    print("VPD_NEXIUM_PRIVATE_ROAD_SD_BOOT_PASS"
          " guest_loader=yes samples=37"
          " data=entirely_synthetic"
          " source_road_physics_proven=no")

if __name__=="__main__":main()
