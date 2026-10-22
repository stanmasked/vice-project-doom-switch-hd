#!/usr/bin/env python3
"""Analyze only owner-local FCEUX CSV. Never emit original pixel values or media."""
import argparse
import csv
import json
from pathlib import Path

def analyze(path):
    with path.open(newline="",encoding="utf-8") as handle:
        rows=list(csv.DictReader(handle))
    required={"frame","movie_active","ram_0000","ram_0010","ram_0100","pixel_128_120"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Missing expected private capture fields")
    frames=[int(row["frame"]) for row in rows]
    if frames != list(range(frames[0], frames[-1]+1)):
        raise ValueError("Discontinuous frame sequence")
    if any(row["movie_active"]!="1" for row in rows):
        raise ValueError("FM2 playback was not continuously active")
    result={"frame_count":len(rows),"first_frame":frames[0],"last_frame":frames[-1],
            "frame_sequence_continuous":True,"fm2_active_all_frames":True,
            "signals":{}}
    for column in sorted(required-{"frame","movie_active"}):
        values=[int(row[column]) for row in rows]
        transitions=[frames[i] for i in range(1,len(values)) if values[i]!=values[i-1]]
        result["signals"][column]={"unique_value_count":len(set(values)),
                                    "transition_count":len(transitions),
                                    "transition_frames":transitions}
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture",type=Path,required=True)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    report=analyze(args.capture)
    report["interpretation"]="Signal changes only; gameplay semantics not inferred"
    if args.output:
        if args.output.exists():
            parser.error("Refuse to overwrite a previous private report")
        args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("VPD_PRIVATE_CAPTURE_TIMELINE_PASS frames="+str(report["frame_count"])+" no_original_pixels_exported=yes")

if __name__=="__main__":
    main()
