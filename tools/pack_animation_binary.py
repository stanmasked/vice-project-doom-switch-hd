#!/usr/bin/env python3
"""Pack authored animation JSON into legacy VANM v1 or atlas-bound VANM v2.

Use --atlas to bind timings to the exact validated VPAT pixel payload.
CRC32 is for accidental mismatch detection, not cryptographic authenticity.
"""
import argparse
import json
import struct
import zlib
from pathlib import Path
from build_animation_manifest import STATES, validate

def atlas_identity(atlas):
    if not isinstance(atlas,bytes) or len(atlas)<22 or atlas[:4]!=b"VPAT":
        raise ValueError("Invalid VPAT atlas for animation binding")
    version,w,h,fw,fh,count,flags=struct.unpack_from("<7H",atlas,4)
    if (version!=1 or flags!=0 or not 0<w<=1024 or not 0<h<=1024
        or not 0<fw<=w or not 0<fh<=h or w%fw or h%fh
        or not 0<count<=(w//fw)*(h//fh) or len(atlas)!=22+w*h*4):
        raise ValueError("Invalid VPAT atlas layout for binding")
    expected=struct.unpack_from("<I",atlas,18)[0]
    if zlib.crc32(atlas[22:])&0xffffffff != expected:
        raise ValueError("Invalid VPAT pixel checksum for binding")
    return count,expected

def pack(data,atlas=None):
    validate(data)
    frames=[]
    desc=bytearray()
    for state in STATES:
        clip=data["states"][state]
        start=len(frames)
        frames.extend((f["frame"],f["ticks"]) for f in clip["frames"])
        desc.extend(struct.pack("<HBB",start,len(clip["frames"]),int(clip["loop"])))
    if len(frames)>256:
        raise ValueError("VANM supports at most 256 total animation frames")
    payload=bytes(desc)+b"".join(struct.pack("<HH",*f) for f in frames)
    version=2 if atlas is not None else 1
    if version==2:
        count,crc=atlas_identity(atlas)
        if count!=data["atlas_frame_count"]:
            raise ValueError("VANM/VPAT frame-count mismatch")
        payload=struct.pack("<I",crc)+payload
    header=b"VANM"+struct.pack("<5H",version,data["atlas_frame_count"],
                                4,len(frames),0)
    header+=struct.pack("<I",zlib.crc32(payload)&0xffffffff)
    return header+payload

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest",type=Path)
    p.add_argument("output",type=Path)
    p.add_argument("--atlas",type=Path,
        help="Validated VPAT texture to bind (writes VANM v2; omit for legacy v1)")
    args=p.parse_args()
    raw=pack(json.loads(args.manifest.read_text(encoding="utf8")),
             args.atlas.read_bytes() if args.atlas is not None else None)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(raw)
    print(f"VANM v{2 if args.atlas else 1}: {len(raw)} bytes, "
          "four animation states"+(" (atlas-bound)" if args.atlas else " (legacy)"))

if __name__=="__main__":main()
