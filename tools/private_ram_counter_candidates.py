#!/usr/bin/env python3
"""Check whether selected RAM bytes track sampled frame number; aggregate-only."""
import argparse
import csv
import json
from pathlib import Path

CANDIDATES=(0x000F,0x0011,0x0016,0x0017,0x0094,0x013A,0x013C)

def analyze(path):
    with Path(path).open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    frames=[int(r["frame"]) for r in rows]
    data=[bytes.fromhex(r["ram_hex"]) for r in rows]
    if len(rows)<3 or frames!=sorted(set(frames)) or any(len(x)!=2048 for x in data):
        raise ValueError("invalid RAM capture")
    out=[]
    for addr in CANDIDATES:
        vals=[x[addr] for x in data]
        deltas=[(vals[i]-vals[i-1])%256 for i in range(1,len(vals))]
        frame_deltas=[frames[i]-frames[i-1] for i in range(1,len(frames))]
        equal=sum(d==fd%256 for d,fd in zip(deltas,frame_deltas))
        zero=sum(d==0 for d in deltas)
        out.append({"address":f"0x{addr:04X}","sample_changes":sum(d!=0 for d in deltas),
                    "sample_intervals":len(deltas),"delta_matches_frame_step":equal,
                    "zero_delta_intervals":zero,"unique_values":len(set(vals))})
    return {"samples":len(rows),"frame_span":[frames[0],frames[-1]],
            "candidate_summary":out,
            "interpretation":"Sparse-sample correlation only; not a semantic identification"}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    s=json.dumps(analyze(a.input),indent=2)+"\n"
    if a.output:
        with a.output.open("x",encoding="utf-8") as f:f.write(s)
    else: print(s)
