#!/usr/bin/env python3
"""Owner-local temporal RAM characterization: aggregate counts, no RAM byte export."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

def analyze(path):
    with Path(path).open(newline="",encoding="utf-8") as stream:
        rows=list(csv.DictReader(stream))
    frames=[int(row["frame"]) for row in rows]
    values=[bytes.fromhex(row["ram_hex"]) for row in rows]
    if len(rows)<3 or any(len(v)!=2048 for v in values) or frames!=sorted(set(frames)):
        raise ValueError("invalid ordered frames or 2 KiB RAM snapshots")
    groups={}
    regular=[]
    for address in range(2048):
        seq=[snapshot[address] for snapshot in values]
        deltas=[(seq[i]-seq[i-1])%256 for i in range(1,len(seq))]
        changes=tuple(i for i,d in enumerate(deltas) if d)
        if changes:
            groups.setdefault(changes,[]).append(address)
        nonzero=[d for d in deltas if d]
        if len(nonzero)>=20:
            delta,count=Counter(nonzero).most_common(1)[0]
            if count/len(nonzero)>=0.85:
                regular.append({"address":f"0x{address:04X}","changes":len(nonzero),
                                "common_mod256_delta":delta,
                                "fraction":round(count/len(nonzero),3)})
    ranked=sorted(groups.items(),key=lambda item:(-len(item[1]),-len(item[0])))
    return {"samples":len(rows),"first_frame":frames[0],"last_frame":frames[-1],
            "changed_signature_groups":len(groups),
            "largest_cochange_groups":[{"addresses":[f"0x{a:04X}" for a in addrs[:12]],
                                         "group_size":len(addrs),"changes":len(sig)}
                                        for sig,addrs in ranked[:12]],
            "regular_delta_candidates":regular[:30],
            "semantics_confirmed":False}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",required=True,type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    report=json.dumps(analyze(args.input),indent=2)+"\n"
    if args.output:
        with args.output.open("x",encoding="utf-8") as out:out.write(report)
    else: print(report)
