#!/usr/bin/env python3
"""Validate author-created animation metadata and generate a C++ table.

The example input is ROM-free. Ticks are authored placeholders, NOT measured
timing from the original game. No JSON parsing/library is needed on Switch.
"""
import argparse
import json
from pathlib import Path

STATES = ("idle", "run", "rise", "fall")


def validate(data):
    if not isinstance(data, dict) or set(data)!={"schema","atlas_frame_count","states"}:
        raise ValueError("Unexpected animation manifest properties")
    if type(data["schema"]) is not int or data["schema"] != 1:
        raise ValueError("Expected schema 1")
    atlas_count = data["atlas_frame_count"]
    if type(atlas_count) is not int or not 1 <= atlas_count <= 4096:
        raise ValueError("Invalid atlas frame count")
    states = data["states"]
    if not isinstance(states, dict) or set(states) != set(STATES):
        raise ValueError("Exactly idle/run/rise/fall states are required")
    for state in STATES:
        clip = states[state]
        if not isinstance(clip, dict) or set(clip) != {"loop","frames"}:
            raise ValueError("Invalid clip properties for "+state)
        if type(clip["loop"]) is not bool:
            raise ValueError("Loop flag must be boolean")
        frames = clip["frames"]
        if not isinstance(frames, list) or not 1 <= len(frames) <= 64:
            raise ValueError("Invalid number of frames for "+state)
        for item in frames:
            if not isinstance(item, dict) or set(item) != {"frame","ticks"}:
                raise ValueError("Invalid frame properties")
            if (type(item["frame"]) is not int or
                type(item["ticks"]) is not int or
                not 0 <= item["frame"] < atlas_count or
                not 1 <= item["ticks"] <= 600):
                raise ValueError("Atlas frame/duration outside supported range")
    return data


def generate_cpp(data):
    validate(data)
    rows = [
        "#pragma once",
        '#include "animation.hpp"',
        "namespace vpd_demo {"
    ]
    for state in STATES:
        frames = data["states"][state]["frames"]
        entries=", ".join("vpd::AnimationFrame{%d, %d}"%(x["frame"],x["ticks"]) for x in frames)
        rows.append("inline constexpr vpd::AnimationFrame k_%s[] = {%s};"%(state,entries))
    rows.append("inline constexpr vpd::AnimationBank kAnimationBank{{")
    for state in STATES:
        clip=data["states"][state]
        rows.append("    {k_%s, %d, %s},"%(state,len(clip["frames"]),"true" if clip["loop"] else "false"))
    rows.extend(["}, %d};"%data["atlas_frame_count"],"}",""])
    return "\n".join(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest",type=Path)
    p.add_argument("header",type=Path)
    args=p.parse_args()
    data=validate(json.loads(args.manifest.read_text(encoding="utf-8")))
    args.header.parent.mkdir(parents=True,exist_ok=True)
    args.header.write_text(generate_cpp(data),encoding="utf-8")
    print("Generated 4 validated clips (authored placeholder timing)")

if __name__=="__main__":
    main()
