#!/usr/bin/env python3
"""Verify that a private FCEUX FM2 movie was observed frame-by-frame.

No original ROM, FM2 input, screenshots, hashes or PPU data are serialized.
This only proves contiguous *observed callbacks* and a read-only terminal
movie state, never correctness of the game's scene or enemy simulation.
"""
import re
from pathlib import Path

SCHEMA="private_fm2_terminal_witness_v2"
REQUIRED={
    "format","movie_readonly","movie_terminal_frame","movie_frame_count",
    "movie_first_observed_frame","movie_last_observed_frame",
    "movie_consecutive_unique_frames","movie_frame_gaps",
    "movie_active_before_terminal","movie_mode_at_terminal",
    "original_stage_proven","game_completion_proven"
}
NUMBER=re.compile(r"(?:0|[1-9][0-9]*)\Z")


def audit_movie_witness(path,*,expected_frame_count):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>2048:
        raise ValueError("private FM2 terminal witness missing, linked or oversized")
    if type(expected_frame_count) is not int or not 2<=expected_frame_count<=100000000:
        raise ValueError("invalid expected FM2 frame count")
    text=path.read_text(encoding="ascii")
    data={}
    for line in text.splitlines():
        if "=" not in line:
            raise ValueError("malformed private FM2 witness row")
        key,val=line.split("=",1)
        if not key or key in data:
            raise ValueError("duplicate or empty FM2 witness key")
        data[key]=val
    if data.keys()!=REQUIRED or data["format"]!=SCHEMA:
        raise ValueError("missing, extra or legacy FM2 witness fields")
    for key in ("movie_readonly","movie_active_before_terminal"):
        if data[key]!="yes":
            raise ValueError("FM2 was not verified read-only and active")
    if data["movie_mode_at_terminal"] not in ("playback","finished"):
        raise ValueError("invalid movie terminal mode")
    if data["original_stage_proven"]!="no" or data["game_completion_proven"]!="no":
        raise ValueError("unsubstantiated original-game success claim")
    integer_keys=("movie_terminal_frame","movie_frame_count",
                  "movie_first_observed_frame","movie_last_observed_frame",
                  "movie_consecutive_unique_frames","movie_frame_gaps")
    values={}
    for key in integer_keys:
        if not NUMBER.fullmatch(data[key]):
            raise ValueError("noncanonical numeric FM2 witness field")
        values[key]=int(data[key])
    first=values["movie_first_observed_frame"]
    last=values["movie_last_observed_frame"]
    count=values["movie_consecutive_unique_frames"]
    frames=values["movie_frame_count"]
    if frames!=expected_frame_count or values["movie_terminal_frame"]!=frames-1:
        raise ValueError("movie terminal frame or length differs from expected FM2")
    if first not in (0,1):
        raise ValueError("FM2 callback did not start near frame zero")
    if last!=frames-1 or count!=frames-first or values["movie_frame_gaps"]!=0:
        raise ValueError("noncontiguous FM2 callback frame sequence")
    return {
        "frame_count":frames,
        "terminal_frame_verified":last,
        "first_observed_frame":first,
        "consecutive_unique_frames":count,
        "frame_gaps":0,
        "movie_readonly":True,
        "movie_mode_at_terminal":data["movie_mode_at_terminal"],
        "original_stage_proven":False,
        "game_completion_proven":False
    }
