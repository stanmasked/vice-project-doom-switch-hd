#!/usr/bin/env python3
"""Audit a fresh-source same-session road/PPU join without the hashless legacy report.

This is a separate research path. It does NOT replace the strict
build_private_road_ppu_join.py gate, which still requires exact reproduction
of all legacy numeric observations. All full-file hashes and numeric samples
remain in memory; only a sanitized aggregate is printed.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from seal_private_road_ppu_321 import verify as verify_seal
from build_private_road_ppu_join import derive_documents
from audit_private_road_ppu_alignment import audit as audit_numeric


def audit(rom: Path, movie: Path, private_dir: Path) -> dict[str, object]:
    sealed = verify_seal(rom, movie, private_dir)
    if not (
        sealed.get("same_fceux_session_41_rgb_slots_and_321_ppu_frames_sealed")
        is True
        and sealed.get("full_ppu_writer_phase_frame_coverage") == 321
        and sealed.get("source_cpu_events_verified") == 1284
    ):
        raise ValueError("fresh original source capture seal incomplete")

    road_window, ppu = derive_documents(private_dir)
    slots = road_window.get("slots")
    if type(slots) is not list or len(slots) != 41:
        raise ValueError("fresh RGB window must contain all 41 slots")
    accepted = [slot for slot in slots if slot.get("status") == "accepted"]
    ambiguous = [slot for slot in slots if slot.get("status") == "ambiguous"]
    if len(accepted) != 37 or len(ambiguous) != 4 or len(accepted) + len(ambiguous) != 41:
        raise ValueError("fresh RGB window is not 37 accepted / 4 ambiguous")

    # Convert the private 41-slot document into the alignment validator's
    # accepted-only numeric schema. Ambiguous frames remain accounted for
    # in the aggregate, but are never invented or interpolated.
    road = {
        "schema": "road_image_cross_sections_v1",
        "rom_sha256": road_window["rom_sha256"],
        "fm2_sha256": road_window["fm2_sha256"],
        "movie_frame_origin": road_window["movie_frame_origin"],
        "samples": [
            {"frame": slot["frame"], "left": slot["left"], "right": slot["right"]}
            for slot in accepted
        ],
    }
    joined = audit_numeric(road, ppu)
    if (
        joined.get("joined_frames") != 37
        or joined.get("published_anchor_frames") != [600, 744, 800, 920]
        or joined.get("matching_source_identity") is not True
        or joined.get("native_writer_pc_order_verified") is not True
    ):
        raise ValueError("fresh source image/CPU alignment did not pass")

    return {
        "fresh_source_same_session_join_checked": True,
        "fresh_source_road_image_slots": 41,
        "fresh_source_accepted_road_intervals": 37,
        "fresh_source_ambiguous_road_intervals": 4,
        "fresh_source_cpu_movie_frames": 321,
        "fresh_source_cpu_writer_events": 1284,
        "fresh_source_ppu_writes_checked": 1284,
        "original_cross_source_anchor_pairs_checked": 4,
        "same_full_file_rom_fm2_identity_in_ephemeral_docs": True,
        "legacy_hashless_numeric_report_compared": False,
        "legacy_exact_reproduction_claimed": False,
        "strict_legacy_join_gate_replaced": False,
        "effective_ppu_scroll_proven": False,
        "camera_speed_proven": False,
        "collision_geometry_proven": False,
        "raw_source_values_disclosed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--movie", required=True, type=Path)
    parser.add_argument("--private-dir", required=True, type=Path)
    args = parser.parse_args()
    summary = audit(args.rom, args.movie, args.private_dir)
    print(
        "VPD_PRIVATE_FRESH_SOURCE_ROAD_PPU_ALIGNMENT_PASS"
        f" rgb_slots={summary['fresh_source_road_image_slots']}"
        f" accepted={summary['fresh_source_accepted_road_intervals']}"
        f" ambiguous={summary['fresh_source_ambiguous_road_intervals']}"
        f" cpu_frames={summary['fresh_source_cpu_movie_frames']}"
        f" cpu_writes={summary['fresh_source_cpu_writer_events']}"
        f" anchors={summary['original_cross_source_anchor_pairs_checked']}"
        " legacy_exact_match=no raw_values_disclosed=no"
        " effective_scroll_proven=no"
    )


if __name__ == "__main__":
    main()
