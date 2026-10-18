#!/usr/bin/env python3
"""Strict parsing of FCEUX Stage147 positive raw-pixel source witnesses.

This parser does not inspect original Vice assets; it requires genuine
instrumented newppu output and rejects incomplete, forged or contradicted
source diagnostics even if final XBuf colors happen to match.
"""
import re

PASS="VPD_STAGE147_NATIVE_FRAME_COLOR_SOURCE_PASS"
NATIVE_FRAME="VPD_STAGE141_NATIVE_FRAME_RESET_PASS"
REJECT="VPD_STAGE141_REJECTED_FRAME_RESET"
PATTERN=re.compile(
    r"^VPD_STAGE147_NATIVE_FRAME_COLOR_SOURCE_PASS "
    r"case=(eight_visible|nine_overflow) "
    r"first_raw=(\d+) second_raw=(\d+) "
    r"first_sprite=(\d+) second_sprite=(\d+) "
    r"first_bgpattern=(\d+) second_bgpattern=(\d+) "
    r"first_xbuf=(\d+) second_xbuf=(\d+) "
    r"samples=16 invalid=0 native_fceux=yes synthetic_only=yes "
    r"original_game_color_source_proven=no$",re.MULTILINE)


class ColorSourceError(ValueError):
    pass


def _number(value):
    number=int(value)
    if str(number)!=value:
        raise ColorSourceError("Noncanonical raw FCEUX color evidence")
    return number


def verify(log,case):
    if (case not in ("eight_visible","nine_overflow") or
            not isinstance(log,str) or log.count(PASS)!=1 or
            log.count(NATIVE_FRAME)!=1 or REJECT in log):
        raise ColorSourceError("Positive source witness missing or contradicted")
    items=list(PATTERN.finditer(log))
    if len(items)!=1:
        raise ColorSourceError("Malformed native pixel provenance")
    name,*values=items[0].groups()
    nums=tuple(_number(v) for v in values)
    expected=(15,15,0,0,0,0,143,143) if case=="nine_overflow" else (
        42,42,1,1,0,0,170,170)
    if name!=case or nums!=expected:
        raise ColorSourceError("Real FCEUX pixel provenance differs from fixture")
    return {"case":name,"raw_colors":nums[:2],
            "sprite_pixels":nums[2:4],"background_patterns":nums[4:6],
            "xbuf_colors":nums[6:8],"samples":16,
            "original_game_color_source_proven":False}
