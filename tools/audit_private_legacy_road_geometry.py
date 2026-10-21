#!/usr/bin/env python3
"""Validate a pre-existing owner-private numeric FCEUX road mask report.

This audits already-extracted RGB *measurements*, never RGB files or ROM
bytes. This legacy report has NO embedded ROM/FM2 hashes: do not interpret
its success as proof of cross-session source identity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_private_road_ppu_window import MOVIE_FRAMES, PUBLISHED_IMAGE

ROOT_FIELDS = {
    "schema", "source", "capture_start", "capture_stop",
    "interval_frames", "capture_count", "observed_callback_gaps",
    "capture_status", "methods", "frames", "limitations", "summary",
}
VALID_FIELDS = {
    "frame", "roi_valid", "observed_left_edge", "observed_right_edge",
    "observed_width", "observed_center_x", "valid_scanline_count",
}
REJECTED_FIELDS = {"frame", "roi_valid", "valid_scanline_count"}
SUMMARY_FIELDS = {
    "valid_frames", "rejected_ambiguous_frames", "minimum_observed_width",
    "maximum_observed_width", "minimum_observed_center_x",
    "maximum_observed_center_x",
}
# Exact four unusable slots in this *specific* existing numeric report.
LEGACY_AMBIGUOUS = {712, 720, 728, 736}


def integer(v: object, low: int, high: int, name: str) -> int:
    if type(v) is not int or not low <= v <= high:
        raise ValueError(f"invalid integer {name}")
    return v


def validate_legacy_report(report: dict) -> dict:
    if type(report) is not dict or set(report) != ROOT_FIELDS:
        raise ValueError("legacy report schema incorrect or leaked media")
    if report["schema"] != "vice-stage1-private-road-mask-scan-v1":
        raise ValueError("wrong numeric source report version")
    if (report["capture_start"], report["capture_stop"],
        report["interval_frames"], report["capture_count"],
        report["observed_callback_gaps"]) != (600, 920, 8, 41, 0):
        raise ValueError("original 41-slot callback window incomplete")
    if report["capture_status"] != "complete local focused window":
        raise ValueError("not an independently completed FCEUX report")
    if type(report["source"]) is not str or "FCEUX" not in report["source"]:
        raise ValueError("original source provenance not documented")
    m = report["methods"]
    if type(m) is not dict or set(m) != {
        "palette_or_rgb", "scanlines_y", "validity",
        "units", "interpretation",
    } or m["scanlines_y"] != [120,140,160,180]:
        raise ValueError("original measurement method changed")
    if type(report["limitations"]) is not list or not report["limitations"]:
        raise ValueError("original ambiguity limitations missing")
    records = report["frames"]
    if type(records) is not list or len(records) != 41:
        raise ValueError("must contain exactly 41 source frame measurements")
    accepted = {}
    rejected = set()
    for expected_frame, row in zip(MOVIE_FRAMES, records):
        if type(row) is not dict or type(row.get("frame")) is not int or (
            row["frame"] != expected_frame
        ):
            raise ValueError("missing, duplicate or out-of-order movie frame")
        valid = row.get("roi_valid")
        if type(valid) is not bool:
            raise ValueError("ROI valid marker must be actual bool")
        if valid:
            if set(row) != VALID_FIELDS:
                raise ValueError("valid source row missing numeric dimensions")
            n = integer(row["valid_scanline_count"],3,4,"usable scanlines")
            left = integer(row["observed_left_edge"],0,255,"visible left")
            right = integer(row["observed_right_edge"],0,255,"visible right")
            width = integer(row["observed_width"],30,200,"visible width")
            center = row["observed_center_x"]
            if (type(center) not in (int,float) or left>right or
                width!=right-left+1 or 2*center!=left+right):
                raise ValueError("numeric road width/center inconsistent")
            accepted[expected_frame] = (left,right,width,center,n)
        else:
            if set(row) != REJECTED_FIELDS:
                raise ValueError("ambiguous frame must not invent dimensions")
            integer(row["valid_scanline_count"],0,2,"ambiguous scanlines")
            rejected.add(expected_frame)
    if len(accepted)!=37 or rejected!=LEGACY_AMBIGUOUS:
        raise ValueError("not the independently observed 37/4 selection")
    for frame,edges in PUBLISHED_IMAGE.items():
        if frame not in accepted or accepted[frame][:2]!=edges:
            raise ValueError("published original image edge anchor changed")
    s=report["summary"]
    if type(s) is not dict or set(s)!=SUMMARY_FIELDS:
        raise ValueError("legacy numeric summary schema invalid")
    computed={
        "valid_frames":len(accepted),
        "rejected_ambiguous_frames":len(rejected),
        "minimum_observed_width":min(x[2] for x in accepted.values()),
        "maximum_observed_width":max(x[2] for x in accepted.values()),
        "minimum_observed_center_x":min(x[3] for x in accepted.values()),
        "maximum_observed_center_x":max(x[3] for x in accepted.values()),
    }
    if computed!=s:
        raise ValueError("summary differs from source numeric observations")
    return {
        "movie_first_frame":600,
        "movie_last_frame":920,
        "numeric_road_slots":41,
        "accepted_visible_cross_sections":37,
        "ambiguous_cross_sections":4,
        "source_callback_gaps":0,
        "published_road_anchors":len(PUBLISHED_IMAGE),
        "original_media_included":False,
        "rom_fm2_hash_identity_confirmed_by_this_report":False,
        "display_effective_scroll_proven":False,
        "camera_speed_proven":False,
        "road_collision_proven":False,
    }


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--numeric-report",type=Path,required=True)
    parser.add_argument("--summary",type=Path)
    args=parser.parse_args()
    source=json.loads(args.numeric_report.read_text("utf8"))
    validated=validate_legacy_report(source)
    if args.summary:
        args.summary.write_text(
            json.dumps(validated,sort_keys=True,indent=2)+"\n",encoding="utf8")
    print("VPD_LEGACY_FCEUX_ROAD_NUMERIC_PASS"
          " road_slots=41 accepted=37 ambiguous=4"
          " source_identity_proven_by_report=no original_media=no")


if __name__=="__main__":
    main()
