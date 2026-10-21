#!/usr/bin/env python3
"""Compare all seven FCEUX-derived numeric swatches with real NeXium X11.

All source references are seven already published *numeric* original
RGB-road measurements. The captured screenshots are the user's synthetic
Nintendo Switch diagnostic, not original NES screenshots or game sprites.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from audit_nexium_driving_live import p6_payload
from audit_nexium_road_x11_shape import ROWS, detect_strip, SIZE
from audit_nexium_road_review import ORIGINAL


def validate_sweep(images: list[bytes]) -> dict:
    if len(images)!=8:
        raise ValueError("need exact seven original numerical image references and OFF")
    if len(ORIGINAL)!=8 or ORIGINAL[-1]!=(0,0,0):
        raise ValueError("published numerical reference sequence changed")
    expected_bytes=SIZE[0]*SIZE[1]*3
    strips=[]
    for index,image in enumerate(images):
        if len(image)!=expected_bytes:
            raise ValueError("incomplete or wrongly sized X11 screenshot")
        observations=[detect_strip(image,row) for row in ROWS]
        if index==7:
            if any(s is not None for s in observations):
                raise ValueError("OFF frame still contains a measurement band")
            continue
        if any(s is None for s in observations) or len(set(observations))!=1:
            raise ValueError("measurement band missing, interrupted or row-inconsistent")
        strips.append(observations[0])

    original_nominal=[(right-left+1)*5-10 for (_,left,right) in ORIGINAL[:7]]
    if min(original_nominal)<=0:
        raise ValueError("no valid published numeric intervals")
    # Recover the COMMON X11 display scale from the first and narrowest
    # observed swatch, without assuming a window x-offset or NES camera.
    scale_first=strips[0].width/original_nominal[0]
    scale_narrow=strips[4].width/original_nominal[4]
    if not 0.8<=scale_first<=1.10 or abs(scale_first-scale_narrow)>0.025:
        raise ValueError("two independent swatches disagree on window scale")
    for index,(strip,nominal) in enumerate(zip(strips,original_nominal)):
        expected_width=nominal*scale_first
        if abs(strip.width-expected_width)>8:
            raise ValueError(f"original RGB width mismatch in swatch {index+1}")
        if (strip.left_border<3 or strip.right_border<3 or
            abs(strip.left_border-strip.right_border)>3):
            raise ValueError("unequal/invalid authored measurement borders")
    # Relative X changes must be consistent across ALL seven screenshots,
    # not only samples 600 and 800. Offsets cancel; source-space centroids
    # are observations, NOT real road world coordinates or camera velocity.
    src_center=[(left+right)/2 for (_,left,right) in ORIGINAL[:7]]
    first_center=(strips[0].first+strips[0].last)/2
    for i,s in enumerate(strips):
        center=(s.first+s.last)/2
        predicted_shift=(src_center[i]-src_center[0])*5*scale_first
        if abs((center-first_center)-predicted_shift)>12:
            raise ValueError(f"swatch {i+1} did not follow measured source X shift")
    delta_67=(strips[6].first+strips[6].last-
              strips[5].first-strips[5].last)/2
    expected_delta=(src_center[6]-src_center[5])*5*scale_first
    if expected_delta<130 or abs(delta_67-expected_delta)>12:
        raise ValueError("late 840→920 lateral source-image shift not displayed")
    if not strips[2].width>strips[3].width>strips[4].width:
        raise ValueError("sampled road did not progressively narrow")
    if not strips[5].width>strips[4].width:
        raise ValueError("sampled road did not widen after narrowest frame")
    if abs(strips[0].width-strips[1].width)>4:
        raise ValueError("equal-width original frames 600/744 lost")
    if abs(strips[5].width-strips[6].width)>4:
        raise ValueError("equal-width original frames 840/920 lost")
    return {
        "real_x11_reference_frames":7,
        "real_x11_off_frames":1,
        "road_narrow_then_widen":True,
        "source_image_lateral_shift_visible":True,
        "seven_exact_numeric_references_checked":True,
        "window_x_offset_assumed":False,
        "original_game_camera_speed_proven":False,
        "original_road_collision_proven":False,
        "original_art_included":False,
    }


def audit(folder:Path)->dict:
    images=[p6_payload(folder/f"screen-review-{i}.ppm")
            for i in range(1,9)]
    result=validate_sweep(images)
    print("VPD_NEXIUM_ROAD_X11_SWEEP_PASS"
          " original_numeric_frames=7 off=1"
          " image_widths_and_centers=yes"
          " late_lateral_shift=yes"
          " source_game_camera_proven=no"
          " original_art_included=no")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence",type=Path,required=True)
    audit(parser.parse_args().evidence)
