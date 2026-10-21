#!/usr/bin/env python3
"""Fail-closed validation of a COMPLETE private numeric Stage 1-1 window.

This consumes only locally audited numeric JSON, not original ROM, FM2,
CHR, PPU arrays, RGB images, absolute source paths, or extracted art.
Actual full-window reports are not supplied in this repository.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_private_road_ppu_alignment import audit as audit_pairs, strict_int

FIRST, LAST, STEP = 600, 920, 8
MOVIE_FRAMES = tuple(range(FIRST, LAST + 1, STEP))    # 41 RGB slots
CPU_FRAMES = tuple(range(FIRST, LAST + 1))           # 321 CPU frames
PUBLISHED_IMAGE = {
    600: (66, 188), 744: (66, 188), 760: (82, 173),
    784: (98, 156), 800: (100, 155), 840: (84, 171),
    920: (116, 203),
}
WINDOW_KEYS = {
    "schema", "rom_sha256", "fm2_sha256", "movie_frame_origin", "slots"
}
ACCEPTED_KEYS = {"frame", "status", "left", "right"}
REJECTED_KEYS = {"frame", "status"}


def validate_complete_window(road_window: dict, ppu: dict) -> dict:
    if type(road_window) is not dict or set(road_window) != WINDOW_KEYS:
        raise ValueError("road report includes unsupported source material")
    if road_window["schema"] != "road_image_cross_sections_window_v1":
        raise ValueError("expected independently audited full-window format")
    if road_window["movie_frame_origin"] != "zero_based_FM2":
        raise ValueError("mixed frame origins")
    slots = road_window["slots"]
    if type(slots) is not list or len(slots) != len(MOVIE_FRAMES):
        raise ValueError("need all 41 source image-slot results")
    accepted, rejected = [], []
    for expected, slot in zip(MOVIE_FRAMES, slots):
        if type(slot) is not dict or slot.get("frame") != expected or (
            type(slot.get("frame")) is not int
        ):
            raise ValueError("missing, duplicated, or unsorted 8-frame RGB slot")
        status = slot.get("status")
        if status == "accepted" and set(slot) == ACCEPTED_KEYS:
            left = strict_int(slot["left"], 0, 255, "source visible left")
            right = strict_int(slot["right"], 0, 255, "source visible right")
            if left > right:
                raise ValueError("negative source RGB segment width")
            accepted.append({"frame": expected, "left": left, "right": right})
        elif status == "ambiguous" and set(slot) == REJECTED_KEYS:
            rejected.append(expected)
        else:
            raise ValueError("ambiguous slot may not invent road boundaries")
    if len(accepted) != 37 or len(rejected) != 4:
        raise ValueError("original source RGB selection count differs from 37/4")
    accepted_by_frame = {item["frame"]: item for item in accepted}
    for frame, (left, right) in PUBLISHED_IMAGE.items():
        entry = accepted_by_frame.get(frame)
        if entry is None or (entry["left"], entry["right"]) != (left, right):
            raise ValueError("published original RGB road anchor not preserved")
    if type(ppu) is not dict or type(ppu.get("samples")) is not list:
        raise ValueError("missing independent PPU source")
    if len(ppu["samples"]) != len(CPU_FRAMES):
        raise ValueError("not all 321 original CPU writer frames supplied")
    for expected, sample in zip(CPU_FRAMES, ppu["samples"]):
        if type(sample) is not dict or type(sample.get("frame")) is not int or (
            sample["frame"] != expected
        ):
            raise ValueError("CPU frame skipped, duplicated, or reordered")
    # Use the independent Stage168 validator for provenance, exact writer
    # sequence, raw $2005 values, source phases, ROM and FM2 identities,
    # and previously confirmed cross-source anchor pairs.
    road = {key: road_window[key] for key in
            ("rom_sha256", "fm2_sha256", "movie_frame_origin")}
    road["schema"] = "road_image_cross_sections_v1"
    road["samples"] = accepted
    verified = audit_pairs(road, ppu)
    if verified["joined_frames"] != 37:
        raise ValueError("complete original image/CPU join unexpectedly partial")
    return {
        "movie_first_frame": FIRST,
        "movie_last_frame": LAST,
        "road_slots_checked": len(MOVIE_FRAMES),
        "road_cross_sections_accepted": len(accepted),
        "road_slots_ambiguous": len(rejected),
        "cpu_frames_checked": len(CPU_FRAMES),
        "source_ppu_writes_checked": len(CPU_FRAMES) * 4,
        "frame_join_verified": True,
        "source_rom_fm2_identity_verified": True,
        "published_image_anchors_checked": len(PUBLISHED_IMAGE),
        "published_ppu_image_pairs_checked": 4,
        "camera_speed_proven": False,
        "effective_display_scroll_proven": False,
        "collision_boundaries_proven": False,
        "source_media_included": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--road-window", type=Path, required=True)
    parser.add_argument("--ppu", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    summary = validate_complete_window(
        json.loads(args.road_window.read_text("utf8")),
        json.loads(args.ppu.read_text("utf8")))
    if args.output:
        args.output.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", "utf8")
    print("VPD_PRIVATE_FULL_ROAD_PPU_WINDOW_PASS"
          " movie_frames=321 road_slots=41 accepted=37 ambiguous=4"
          " raw_ppu_writes=1284 camera_speed_proven=no original_assets=no")


if __name__ == "__main__":
    main()
