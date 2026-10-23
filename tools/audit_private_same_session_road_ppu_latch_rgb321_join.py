#!/usr/bin/env python3
"""Join fresh same-session RGB road edges with CPU/PPU/RAM evidence in memory only."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from audit_private_road_mask_reproduction import (
    LEGACY_AMBIGUOUS,
    extract_report,
)
from audit_private_road_ppu_alignment import audit as audit_numeric_alignment
from audit_private_road_ppu_latch_rgb321 import (
    PRE,
    PRE_FIELDS,
    verify as verify_same_session_capture,
)

WRITER_FIELDS = ["frame", "ordinal", "pc", "value", "cycle"]
RAM_FIELDS = ["frame", "ram_0d", "ppu_2005_writes"]
CLOCK_FIELDS = ["frame", "begin_cycle", "end_cycle"]
EXPECTED_WRITER_PCS = ["E8EC", "E8F1", "E369", "E36C"]
EXPECTED_AMBIGUOUS = sorted(LEGACY_AMBIGUOUS)


def _read_tsv(path: Path, fields: list[str]) -> list[dict[str, str]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("private same-session numeric source missing or linked")
    with path.open("r", encoding="ascii", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != fields:
            raise ValueError("private same-session numeric source schema mismatch")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("private same-session numeric source row truncated")
    return rows


def derive_numeric_documents(folder: Path, identity: dict) -> tuple[dict, dict, dict]:
    """Build ephemeral numeric-only documents; never write or print them."""
    if type(identity) is not dict or not {
        "rom_sha256", "fm2_sha256"
    } <= set(identity):
        raise ValueError("same-session source identity unavailable")

    road_slots = extract_report(folder / "road_321_rgb_scanlines.bin")
    if len(road_slots) != 41 or [row["frame"] for row in road_slots] != list(range(600, 921, 8)):
        raise ValueError("fresh source RGB slot coverage/order invalid")
    accepted = [row for row in road_slots if row["roi_valid"]]
    ambiguous = sorted(row["frame"] for row in road_slots if not row["roi_valid"])
    if len(accepted) != 37 or ambiguous != EXPECTED_AMBIGUOUS:
        raise ValueError("fresh source RGB must retain 37 accepted and four known ambiguous slots")

    headers = {
        "rom_sha256": identity["rom_sha256"],
        "fm2_sha256": identity["fm2_sha256"],
        "movie_frame_origin": "zero_based_FM2",
    }
    road = {
        "schema": "road_image_cross_sections_v1",
        **headers,
        "samples": [
            {
                "frame": row["frame"],
                "left": row["observed_left_edge"],
                "right": row["observed_right_edge"],
            }
            for row in accepted
        ],
    }

    writers = _read_tsv(folder / "road_321_writers.tsv", WRITER_FIELDS)
    ram_rows = _read_tsv(folder / "road_321_postframe.tsv", RAM_FIELDS)
    clocks = _read_tsv(folder / "source_frame_clock.tsv", CLOCK_FIELDS)
    if len(writers) != 1284 or len(ram_rows) != 321 or len(clocks) != 321:
        raise ValueError("same-session CPU/RAM/frame-clock coverage incomplete")

    writer_by_frame: dict[int, list[dict[str, str]]] = {}
    for row in writers:
        frame = int(row["frame"])
        writer_by_frame.setdefault(frame, []).append(row)
    ram_by_frame = {int(row["frame"]): row for row in ram_rows}
    clock_by_frame = {int(row["frame"]): row for row in clocks}
    if (
        set(writer_by_frame) != set(range(600, 921))
        or set(ram_by_frame) != set(range(600, 921))
        or set(clock_by_frame) != set(range(600, 921))
    ):
        raise ValueError("same-session CPU/RAM/clock frame identities differ")

    ppu = {
        "schema": "ppu_cpu_writer_phases_v1",
        **headers,
        "samples": [],
    }
    for frame in range(600, 921):
        cpu_rows = writer_by_frame[frame]
        if (
            len(cpu_rows) != 4
            or [int(row["ordinal"]) for row in cpu_rows] != [1, 2, 3, 4]
            or [row["pc"] for row in cpu_rows] != EXPECTED_WRITER_PCS
        ):
            raise ValueError("same-session CPU writer PC/order sequence changed")
        clock = clock_by_frame[frame]
        ram = ram_by_frame[frame]
        begin = int(clock["begin_cycle"])
        values = [int(row["value"], 16) for row in cpu_rows]
        phases = [int(row["cycle"]) - begin for row in cpu_rows]
        ppu["samples"].append({
            "frame": frame,
            "writer_pcs": list(EXPECTED_WRITER_PCS),
            "written_values": values,
            "cpu_cycles_after_previous_frame": phases,
            "ram_0d_postframe": int(ram["ram_0d"], 16),
        })

    return road, ppu, {
        "rgb_slots": len(road_slots),
        "accepted_intervals": len(accepted),
        "ambiguous_intervals": len(ambiguous),
        "ambiguous_frames": ambiguous,
        "cpu_frames": len(ppu["samples"]),
        "cpu_writer_events": len(writers),
    }


def audit(rom: Path, movie: Path, folder: Path) -> dict:
    capture = verify_same_session_capture(rom, movie, folder)
    if capture.get("same_session_cpu_ram_ppu_rgb_joined") is not True:
        raise ValueError("same-session source capture has not passed its complete audit")
    identity_path = folder / PRE
    if identity_path.is_symlink() or not identity_path.is_file():
        raise ValueError("same-session source identity manifest missing or linked")
    identity = json.loads(identity_path.read_text(encoding="utf8"))
    if type(identity) is not dict or set(identity) != PRE_FIELDS:
        raise ValueError("same-session source identity manifest schema invalid")
    road, ppu, coverage = derive_numeric_documents(folder, identity)
    joined = audit_numeric_alignment(road, ppu)
    if (
        joined.get("joined_frames") != 37
        or joined.get("published_anchor_frames") != [600, 744, 800, 920]
        or joined.get("matching_source_identity") is not True
        or joined.get("native_writer_pc_order_verified") is not True
    ):
        raise ValueError("fresh source RGB-to-CPU/PPU/RAM numeric join incomplete")
    return {
        **coverage,
        "published_road_ppu_ram_anchor_pairs_checked": 4,
        "same_full_file_rom_fm2_identity_in_ephemeral_documents": True,
        "ephemeral_numeric_documents_written_to_disk": False,
        "raw_rgb_or_source_values_disclosed": False,
        "legacy_hashless_report_authenticated": False,
        "effective_ppu_scroll_proven": False,
        "camera_speed_proven": False,
        "collision_geometry_proven": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--movie", required=True, type=Path)
    parser.add_argument("--private-dir", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.rom, args.movie, args.private_dir)
    print(
        "VPD_PRIVATE_SAME_SESSION_ROAD_PPU_RGB_JOIN_PASS"
        f" rgb_slots={result['rgb_slots']}"
        f" accepted={result['accepted_intervals']}"
        f" ambiguous={result['ambiguous_intervals']}"
        f" cpu_frames={result['cpu_frames']}"
        f" cpu_writes={result['cpu_writer_events']}"
        f" anchor_pairs={result['published_road_ppu_ram_anchor_pairs_checked']}"
        " same_source_identity=yes ephemeral_docs_only=yes"
        " legacy_hashless_report_authenticated=no"
        " effective_ppu_scroll_proven=no raw_values_disclosed=no"
    )


if __name__ == "__main__":
    main()
