#!/usr/bin/env python3
"""Analyze private 2 KiB NES RAM samples by fixed time windows; export counts only."""
import argparse
import csv
import json
from pathlib import Path

WINDOWS=((1,270,"pre-input"),(271,400,"post-first-input"),(401,600,"late-intro"))

def analyze(path):
    with path.open(newline="",encoding="utf-8") as stream:
        rows=list(csv.DictReader(stream))
    if not rows or set(rows[0])!={"frame","ram_hex"}:
        raise ValueError("incorrect CSV columns")
    frames=[int(row["frame"]) for row in rows]
    if frames!=sorted(set(frames)):
        raise ValueError("frames must strictly increase")
    samples=[(frame,bytes.fromhex(row["ram_hex"])) for frame,row in zip(frames,rows)]
    if any(len(data)!=2048 for _,data in samples):
        raise ValueError("each snapshot must have 2048 bytes")
    result=[]
    for start,end,name in WINDOWS:
        segment=[(frame,data) for frame,data in samples if start<=frame<=end]
        if len(segment)<2:
            raise ValueError("not enough samples in "+name)
        counts=[sum(segment[i][1][addr]!=segment[i-1][1][addr]
                    for i in range(1,len(segment))) for addr in range(2048)]
        ranked=sorted(range(2048),key=lambda a:(-counts[a],a))[:12]
        result.append({"name":name,"window":[start,end],"samples":len(segment),
                       "changing_addresses":sum(x>0 for x in counts),
                       "top_addresses":[{"address":f"0x{addr:04X}",
                                         "transitions":counts[addr]} for addr in ranked]})
    return {"segments":result,"gameplay_semantics_confirmed":False}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    data=json.dumps(analyze(args.input),indent=2)+"\n"
    if args.output:
        with args.output.open("x",encoding="utf-8") as out:out.write(data)
    else:print(data)
