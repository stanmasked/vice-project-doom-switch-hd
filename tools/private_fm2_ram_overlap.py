#!/usr/bin/env python3
"""Private exploratory FM2 button/RAM transition alignment; no game data in Git."""
import argparse
import csv
import json
from pathlib import Path


def analyze(csv_path: Path, fm2_path: Path):
    with csv_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("Capture is empty")
    frames = [int(r["frame"]) for r in rows]
    if frames != list(range(1, len(rows) + 1)):
        raise ValueError("Capture must be continuous starting at frame 1")
    if any(r["movie_active"] != "1" for r in rows):
        raise ValueError("FM2 not active on every captured frame")
    buttons = [line.split("|")[2] for line in
               fm2_path.read_text(encoding="utf-8").splitlines()
               if line.startswith("|")]
    if len(buttons) < len(rows):
        raise ValueError("FM2 shorter than capture")
    active = {i + 1 for i, value in enumerate(buttons[:len(rows)])
              if value != "........"}
    result = {"frames": len(rows), "active_input_frames": len(active),
              "first_active_frame": min(active) if active else None,
              "signals": {},
              "interpretation": "Temporal overlap only, not causality or address identification"}
    for field in ("ram_0000", "ram_0010", "ram_0100", "pixel_128_120"):
        if field not in rows[0]:
            raise ValueError(f"Missing capture field {field}")
        transitions = {i + 1 for i in range(1, len(rows))
                       if rows[i][field] != rows[i - 1][field]}
        result["signals"][field] = {
            "transitions": len(transitions),
            "same_frame_active_input_overlap": len(transitions & active)
        }
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, required=True)
    p.add_argument("--fm2", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(analyze(args.csv, args.fm2), indent=2))
