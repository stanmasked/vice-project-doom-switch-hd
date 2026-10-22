#!/usr/bin/env python3
"""Validate owner-local per-frame candidate RAM CSV and emit aggregate-only summary."""
import argparse
import csv
import json
from pathlib import Path

FIELDS=("ram_000f","ram_0011","ram_0016","ram_0017","ram_0094","ram_013a","ram_013c")

def analyze(path, expected_frames=321):
    with Path(path).open(newline="",encoding="utf-8") as stream:
        rows=list(csv.DictReader(stream))
    expected={"frame",*FIELDS}
    if not rows or set(rows[0])!=expected:
        raise ValueError("unexpected candidate RAM CSV schema")
    frames=[int(row["frame"]) for row in rows]
    if frames!=list(range(frames[0],frames[0]+len(frames))):
        raise ValueError("frame sequence is not continuous")
    if len(rows)!=expected_frames:
        raise ValueError(f"expected {expected_frames} rows, got {len(rows)}")
    report={"frames":len(rows),"first_frame":frames[0],"last_frame":frames[-1],
            "continuous":True,"signals":{},"semantics_confirmed":False}
    for field in FIELDS:
        vals=[int(row[field]) for row in rows]
        transitions=sum(vals[i]!=vals[i-1] for i in range(1,len(vals)))
        report["signals"][field]={"transitions":transitions,
            "unique_values":len(set(vals)),
            "constant_delta_intervals":sum((vals[i]-vals[i-1])%256 == 1 for i in range(1,len(vals)))}
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",required=True,type=Path)
    parser.add_argument("--frames",type=int,default=321)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=json.dumps(analyze(args.input,args.frames),indent=2)+"\n"
    if args.output:
        with args.output.open("x",encoding="utf-8") as f:f.write(result)
    else: print(result)
