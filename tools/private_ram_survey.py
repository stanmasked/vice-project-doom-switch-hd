#!/usr/bin/env python3
"""Owner-local 2 KiB NES RAM survey; writes aggregate statistics, never RAM bytes."""
import argparse
import csv
import json
from pathlib import Path

def analyze(path):
    with path.open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    if not rows or set(("frame","ram_hex"))-set(rows[0]):
        raise ValueError("missing frame or ram_hex column")
    frames=[int(r["frame"]) for r in rows]
    if len(set(frames))!=len(frames) or frames!=sorted(frames):
        raise ValueError("unsorted or duplicate frames")
    snapshots=[bytes.fromhex(r["ram_hex"]) for r in rows]
    if any(len(data)!=2048 for data in snapshots):
        raise ValueError("each RAM snapshot must be 2048 bytes")
    signals=[]
    for addr in range(2048):
        values=[s[addr] for s in snapshots]
        changes=sum(values[i]!=values[i-1] for i in range(1,len(values)))
        if changes:
            signals.append({"address":f"0x{addr:04X}","transitions":changes,
                            "unique_values":len(set(values))})
    return {"samples":len(rows),"first_frame":frames[0],"last_frame":frames[-1],
            "ram_addresses":2048,"changing_addresses":len(signals),
            "constant_addresses":2048-len(signals),
            "top_changing_addresses":sorted(signals,key=lambda x:(-x["transitions"],x["address"]))[:20],
            "semantics_confirmed":False}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    summary=json.dumps(analyze(args.input),indent=2)+"\n"
    if args.output:
        if args.output.exists():p.error("refusing to overwrite report")
        args.output.write_text(summary,encoding="utf-8")
    else:
        print(summary)
