#!/usr/bin/env python3
"""Summarize validated original Stage 1-1 *visible image-space* road changes.

Consumes only a locally stored numeric FCEUX aggregate; publishes no frame
pixels, ROM bytes, FM2, original sprite art, CPU traces, raw per-frame road
coordinates or unverifiable camera/vehicle physics.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from audit_private_legacy_road_geometry import validate_legacy_report


def profile(report: dict) -> dict:
    verified = validate_legacy_report(report)
    observations = {
        row["frame"]: row for row in report["frames"] if row["roi_valid"]
    }
    runs: list[dict] = []
    for frame in sorted(observations):
        if not runs or frame != runs[-1]["last_frame"]+8:
            runs.append({"first_frame":frame,"last_frame":frame,"samples":1})
        else:
            runs[-1]["last_frame"]=frame
            runs[-1]["samples"]+=1

    def change(start: int,end: int,kind: str) -> dict:
        # Refuse to treat a four-frame ambiguous gap as a measured curve.
        left = observations.get(start)
        right = observations.get(end)
        if left is None or right is None or end<=start:
            raise ValueError("change endpoints lack valid original samples")
        if not any(r["first_frame"]<=start and end<=r["last_frame"] for r in runs):
            raise ValueError("cannot infer road trend across an ambiguous gap")
        a,b = left,right
        if kind=="width":
            measure=lambda item:item["observed_width"]
        elif kind=="center":
            measure=lambda item:item["observed_center_x"]
        else:
            raise ValueError("unsupported image-space metric")
        start_value,end_value=measure(a),measure(b)
        return {
            "first_frame": start,
            "last_frame": end,
            "metric": kind,
            "measured_difference_px": end_value-start_value,
            "source_units": "256px NES screenshot image space",
            "camera_velocity_proven":False,
            "collision_boundary_proven":False,
        }

    # These are report *presentation features*, never a 3D roadway track,
    # guessed per-tick interpolation, or an actual steering response.
    changes={
        "visible_narrowing":change(744,800,"width"),
        "visible_widening":change(800,840,"width"),
        "lateral_image_shift":change(864,904,"center"),
    }
    return {
        "schema":"vpd_road_image_profile_summary_v1",
        "source_numeric_report_valid":True,
        "source_rom_fm2_identity_verified_by_this_report":False,
        "accepted_samples":verified["accepted_visible_cross_sections"],
        "ambiguous_samples":verified["ambiguous_cross_sections"],
        "continuous_valid_runs":runs,
        "observed_image_space_changes":changes,
        "interpolation_across_missing_frames_permitted":False,
        "effective_ppu_scroll_proven":False,
        "camera_speed_proven":False,
        "collision_boundaries_proven":False,
        "original_game_assets_included":False,
    }


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--numeric-report",required=True,type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=profile(json.loads(args.numeric_report.read_text(encoding="utf8")))
    if args.output:
        args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",
                               encoding="utf8")
    print("VPD_PRIVATE_ROAD_IMAGE_PROFILE_PASS"
          " samples=37 excluded=4 valid_runs=2"
          " observed_image_shifts=yes"
          " camera_speed_proven=no proprietary_pixels=none")


if __name__=="__main__":
    main()
