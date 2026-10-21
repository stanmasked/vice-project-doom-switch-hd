#!/usr/bin/env python3
"""Independently verify rendered X11 widths of two measured HD road swatches.

This checks actual NeXium-host-screen P6 images, not only the NRO's
source-owned SD pixel logs. Images show INVENTED visualization colors,
never original NES/CHR/PPU art or calibrated original-game road physics.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import NamedTuple
from audit_nexium_driving_live import p6_payload

SIZE=(1280,720)
RGB_FILL=bytes((98,143,132))
RGB_BORDER=bytes((233,190,117))
RGB_PANEL=bytes((14,24,34))
ROWS=(143,156,169,182)
# Source numeric examples: FM2 600 width 123, FM2 800 width 56;
# actual review renderer adds 5 HD pixels of decorative border each side.
SOURCE_REFERENCE_WIDE=123
SOURCE_REFERENCE_NARROW=56
HD_SCALE_X=5
BORDER_TOTAL_HD=10


class Strip(NamedTuple):
    first: int
    last: int
    width: int
    left_border: int
    right_border: int


def _rgb(payload: bytes,y:int,x:int) -> bytes:
    pos=(y*SIZE[0]+x)*3
    return payload[pos:pos+3]


def detect_strip(payload: bytes,row:int) -> Strip|None:
    # Restrict to the viewport's middle; avoid the NeXium FPS overlay and
    # desktop border. No hard-coded window offset or camera coordinate.
    hits=[x for x in range(256,1056)
          if _rgb(payload,row,x)==RGB_FILL]
    if not hits:return None
    left,right=hits[0],hits[-1]
    if len(hits)!=right-left+1:
        raise ValueError("disconnected or corrupted RGB roadway swatch")
    lborder=rborder=0
    while left-lborder-1>=0 and (
        _rgb(payload,row,left-lborder-1)==RGB_BORDER
    ):
        lborder+=1
    while right+rborder+1<SIZE[0] and (
        _rgb(payload,row,right+rborder+1)==RGB_BORDER
    ):
        rborder+=1
    if not (3<=lborder<=8 and 3<=rborder<=8):
        raise ValueError("no intact X11 border next to swatch fill")
    if (_rgb(payload,row,left-lborder-1)!=RGB_PANEL or
        _rgb(payload,row,right+rborder+1)!=RGB_PANEL):
        raise ValueError("X11 swatch lacks original-free panel background")
    return Strip(left,right,right-left+1,lborder,rborder)


def validate_frames(wide:bytes,narrow:bytes,disabled:bytes) -> dict:
    strips={}
    expected_length=SIZE[0]*SIZE[1]*3
    for label,image in (("wide",wide),("narrow",narrow),("disabled",disabled)):
        if len(image)!=expected_length:
            raise ValueError("X11 screenshot not full 1280x720 RGB24")
        found=[detect_strip(image,row) for row in ROWS]
        if label=="disabled":
            if any(s is not None for s in found):
                raise ValueError("OFF gesture left a colored measurement on X11")
            continue
        if any(s is None for s in found):
            raise ValueError(f"{label}: X11 did not display the numeric roadway")
        if len(set(found))!=1:
            raise ValueError(f"{label}: raster interval shifts across fixed Y rows")
        strips[label]=found[0]

    first,second=strips["wide"],strips["narrow"]
    observed=first.width/second.width
    expected=(SOURCE_REFERENCE_WIDE*HD_SCALE_X-BORDER_TOTAL_HD)/(
        SOURCE_REFERENCE_NARROW*HD_SCALE_X-BORDER_TOTAL_HD)
    if abs(observed-expected)/expected>0.045:
        raise ValueError("X11 width ratio contradicts 123→56 source RGB data")
    if first.width<=second.width+200:
        raise ValueError("X11 road review did not visibly narrow")
    if abs((first.first+first.last)-(second.first+second.last))>24:
        raise ValueError("observed source centers should be approximately equal")
    return {
        "wide_x11_fill_width_px":first.width,
        "narrow_x11_fill_width_px":second.width,
        "wide_over_narrow_ratio":round(observed,5),
        "source_reference_x_widths":[123,56],
        "x11_rgb24_nearest_fill_proven":True,
        "independent_host_screenshot_checked":True,
        "original_game_camera_speed_proven":False,
        "original_road_collision_proven":False,
        "original_art_or_rom_included":False,
    }


def audit(folder:Path) -> dict:
    # p6_payload fails closed for unexpected dimensions/headers/pixel formats.
    result=validate_frames(
        p6_payload(folder/"screen-review-1.ppm"),
        p6_payload(folder/"screen-review-5.ppm"),
        p6_payload(folder/"screen-review-8.ppm"))
    print("VPD_NEXIUM_ROAD_X11_SHAPE_PASS"
          f" wide_screen_pixels={result['wide_x11_fill_width_px']}"
          f" narrow_screen_pixels={result['narrow_x11_fill_width_px']}"
          " original_numeric_widths=123_to_56"
          " off_review_absent=yes"
          " source_window_offset_not_assumed=yes"
          " original_game_physics_proven=no")
    return result


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--evidence",required=True,type=Path)
    audit(cli.parse_args().evidence)
