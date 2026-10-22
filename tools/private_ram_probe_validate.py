#!/usr/bin/env python3
"""Validate owner-local per-frame candidate RAM CSV and emit aggregate-only summary."""
import argparse
import csv
import json
from pathlib import Path

FIELDS=("ram_000f","ram_0011","ram_0016","ram_0017","ram_0094","ram_013a","ram_013c")

def analyze(path, expected_frames=321):
    if expected_frames < 1:
        raise ValueError("expected_frames must be positive")
    with Path(path).open(newline="",encoding="utf-8") as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames is None or len(reader.fieldnames)!=len(set(reader.fieldnames)):
            raise ValueError("missing or duplicate CSV headers")
        expected={"frame",*FIELDS}
        if set(reader.fieldnames)!=expected:
            raise ValueError("unexpected candidate RAM CSV schema")
        rows=list(reader)
    if not rows:
        raise ValueError("empty candidate RAM CSV")
    try:
        frames=[int(row["frame"]) for row in rows]
    except (TypeError,ValueError) as exc:
        raise ValueError("frame values must be integers") from exc
    for row in rows:
        for field in FIELDS:
            try:
                value=int(row[field])
            except (TypeError,ValueError) as exc:
                raise ValueError(f"{field} values must be integers") from exc
            if not 0 <= value <= 255:
                raise ValueError(f"{field} values must be bytes")
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
