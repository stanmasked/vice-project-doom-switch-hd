#!/usr/bin/env python3
"""Stage140 pinned FCEUX sprite overflow flag reset across frame boundaries.

This is a source contract + independent model only, not a native
multi-frame FCEUX observation or evidence about Vice: Project Doom.
"""
import argparse
from pathlib import Path

from audit_stage136_oam_eight_limit import (
    OAMLimitError, verify_source, sprite_scanline_model)

FRAME_ANCHORS=(
    'if (VBlankON) TriggerNMI();',
    'int sltodo = PAL?70:20;',
    'for(int S=0;S<sltodo;S++)',
    '//this seems to run just before the dummy scanline begins',
    'PPU_status = 0;',
    '//There are 2 conditions that update all 5 PPU scroll counters',
)

def verify_frame_source(source):
    if isinstance(source,bytes):
        source=source.decode("latin1")
    if not isinstance(source,str):
        raise OAMLimitError("Expected pinned FCEUX C++ text")
    matches=[]
    for anchor in FRAME_ANCHORS:
        if source.count(anchor)!=1:
            raise OAMLimitError("Ambiguous/missing frame reset anchor: "+anchor)
        matches.append(source.index(anchor))
    if matches!=sorted(matches) or matches[-1]-matches[0]>2000:
        raise OAMLimitError("Unexpected VBlank to pre-render reset ordering")
    oam=verify_source(source)
    if not oam["native_source_selection_order"]:
        raise OAMLimitError("Missing source-backed OAM overflow operation")
    if matches[-2]>=source.index("if (oamcount >= 8 && PPUON) {"):
        raise OAMLimitError("Overflow source must follow pre-render reset")
    return {"source_frame_status_reset":True,
            "clears_overflow_bit":0x20,
            "source_sprite_overflow":True,
            "native_multiframe_overflow_proven":False,
            "original_game_multiframe_proven":False}


def frame_sequence(oam_by_frame,*,scanlines=(124,132),height=16):
    if (type(oam_by_frame) not in (tuple,list) or
            len(oam_by_frame)<2 or len(oam_by_frame)>8 or
            type(scanlines) not in (tuple,list) or not scanlines or
            any(type(n) is not int or not 0<=n<240 for n in scanlines) or
            len(set(scanlines))!=len(scanlines) or
            tuple(scanlines)!=tuple(sorted(scanlines)) or
            type(height) is not int or height not in (8,16)):
        raise OAMLimitError("Require ordered frame and scanline evidence")
    reports=[]
    for frame_id,oam_y in enumerate(oam_by_frame):
        # Source: PPU_status=0 before dummy/pre-render scanline.
        status=0
        samples=[]
        for sl in scanlines:
            evidence=sprite_scanline_model(oam_y,sl,height=height)
            if evidence["sprite_overflow_bit"]:
                status|=0x20
            samples.append({
                "row":sl,"count":evidence["selected_count"],
                "selected":evidence["chosen_oam_indexes"],
                "new_overflow":evidence["sprite_overflow_bit"],
                "status_overflow":bool(status&0x20)})
        reports.append({
            "frame":frame_id,"status_after_reset":0,
            "rows":samples,
            "end_overflow":bool(status&0x20)})
    return {
        "frames":reports,"native_multiframe_overflow_proven":False,
        "original_game_multiframe_proven":False}


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("pinned_ppu_cpp",type=Path)
    a=cli.parse_args()
    verify_frame_source(a.pinned_ppu_cpp.read_bytes())
    print("STAGE140_PINNED_OVERFLOW_FRAME_RESET_SOURCE_PASS "
          "source_only=yes overflow_bit=0x20 reset_before_render=yes "
          "native_multiframe_overflow_proven=no "
          "original_game_multiframe_proven=no")
