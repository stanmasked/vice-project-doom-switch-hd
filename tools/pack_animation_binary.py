#!/usr/bin/env python3
"""Convert a validated independently authored animation JSON into VANM v1."""
import argparse
import json
import struct
import zlib
from pathlib import Path
from build_animation_manifest import STATES, validate

def pack(data):
    validate(data)
    frames=[]
    desc=bytearray()
    for state in STATES:
        clip=data["states"][state]
        start=len(frames)
        frames.extend((f["frame"],f["ticks"]) for f in clip["frames"])
        desc.extend(struct.pack("<HBB",start,len(clip["frames"]),int(clip["loop"])))
    if len(frames)>256:
        raise ValueError("VANM v1 supports at most 256 total animation frames")
    payload=bytes(desc)+b"".join(struct.pack("<HH",*f) for f in frames)
    header=b"VANM"+struct.pack("<5H",1,data["atlas_frame_count"],4,len(frames),0)
    header+=struct.pack("<I",zlib.crc32(payload)&0xffffffff)
    return header+payload

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    raw=pack(json.loads(args.manifest.read_text(encoding="utf8")))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(raw)
    print("VANM v1: %d bytes, four animation states"%len(raw))

if __name__=="__main__":main()
