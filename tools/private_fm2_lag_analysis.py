#!/usr/bin/env python3
"""Owner-local exploratory alignment of FM2 inputs with post-frame observations."""
import argparse
import csv
import json
from pathlib import Path

FIELDS = ("ram_0000", "ram_0010", "ram_0100", "pixel_128_120")


def analyze(csv_file: Path, fm2_file: Path, lags=range(-3, 4)):
    with csv_file.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or any(key not in rows[0] for key in ("frame", "movie_active", *FIELDS)):
        raise ValueError("incomplete CSV")
    frames = [int(row["frame"]) for row in rows]
    if frames != list(range(frames[0], frames[0] + len(frames))):
        raise ValueError("noncontiguous frames")
    if any(row["movie_active"] != "1" for row in rows):
        raise ValueError("FM2 inactive")
    with fm2_file.open(encoding="utf-8") as stream:
        inputs = [line.rstrip("\r\n").split("|")[2] for line in stream if line.startswith("|")]
    if not inputs or any(len(entry) != 8 for entry in inputs):
        raise ValueError("malformed FM2 input")
    if frames[-1] > len(inputs):
        raise ValueError("FM2 shorter than capture")
    active = {index for index, entry in enumerate(inputs) if entry != "........"}
    report = {
        "frame_start": frames[0], "frame_end": frames[-1], "rows": len(frames),
        "active_inputs_in_window": sum(frame - 1 in active for frame in frames),
        "lag_convention": "lag d compares transition after frame f to FM2 row (f-1-d); positive d means earlier input",
        "lag_results": {}, "causality_proven": False,
    }
    for field in FIELDS:
        transitions = [frames[index] for index in range(1, len(rows))
                       if rows[index][field] != rows[index - 1][field]]
        overlaps = {}
        for lag in lags:
            eligible = [frame for frame in transitions if 0 <= frame - 1 - lag < len(inputs)]
            overlaps[str(lag)] = {
                "overlap": sum(frame - 1 - lag in active for frame in eligible),
                "eligible_transitions": len(eligible),
            }
        report["lag_results"][field] = {
            "transition_count": len(transitions), "by_lag": overlaps
        }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--fm2", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(analyze(args.csv, args.fm2), indent=2) + "\n"
    if args.output:
        if args.output.exists():
            parser.error("refuse overwrite")
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result)
