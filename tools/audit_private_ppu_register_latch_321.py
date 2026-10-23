#!/usr/bin/env python3
"""Audit a private original-source FCEUX trace of PPU register write-latch roles.

Raw event rows, ROM/FM2 identities, and local paths stay in the owner's private
workspace. This checks direct $2002 read candidates found in PRG code, not all
possible indirect I/O accesses; it does not prove effective raster scroll.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from seal_private_road_ppu_321 import (
    PRE as REFERENCE_PRE,
    PRE_FIELDS as REFERENCE_PRE_FIELDS,
    _create_json,
    _json,
    private_dir,
    sha256_file,
    source_identity,
    verify as verify_source_capture,
)

PRE = "SOURCE_IDENTITY_BEFORE.json"
POST = "SOURCE_IDENTITY_SEALED.json"
VERSION = "vpd-private-ppu-latch321-identity-v1"
ARTIFACTS = (
    "ppu_register_events.tsv",
    "ppu_register_counts.tsv",
    "ppu_register_frame_clock.tsv",
    "COMPLETE.txt",
)
PRE_FIELDS = {
    "format", "rom_sha256", "fm2_sha256", "rom_payload_md5",
    "movie_frames", "movie_power_on",
}
POST_FIELDS = {
    "format", "rom_sha256", "fm2_sha256", "artifact_sha256",
    "content_seal_sha256", "capture_completed",
}
EVENT_FIELDS = [
    "frame", "seq", "type", "address", "size", "value",
    "pc", "opcode", "a", "x", "y", "cycle",
]
CLOCK_FIELDS = ["frame", "begin_cycle", "end_cycle"]
COUNT_TYPES = ("R2002", "W2000", "W2001", "W2002", "W2005", "W2006")
COUNT_KEYS = {
    "frames", "first", "last", *COUNT_TYPES,
    "frame_clock_rows", "total_events", "source_values_disclosed",
}
COMPLETE_KEYS = {
    "format", "frames", "events", "frame_clock_rows",
    "rom_identity_verified", "movie_readonly_verified",
}
SLOT_BASES = (0x8000, 0xA000, 0xC000, 0xE000)
READ_OFFSETS = (
    0x001E, 0x1EA8, 0x03AC, 0x03B1, 0x03C7, 0x062E, 0x0659,
    0x069A, 0x070E, 0x072E, 0x08E7, 0x0923, 0x0928,
    0x1218, 0x1434, 0x1522, 0x1D01,
)
READ_PCS = {base + offset for base in SLOT_BASES for offset in READ_OFFSETS}
WRITE_PC_AFTER = (0xE8EF, 0xE8F4, 0xE36C, 0xE36F)
EXPECTED_ORIGINAL_COUNTS = {
    "R2002": 845, "W2000": 808, "W2001": 642,
    "W2002": 0, "W2005": 1284, "W2006": 6624,
}
MAX_EVENT_BYTES = 50_000_000


def _identity(rom: Path, movie: Path) -> dict:
    data = source_identity(rom, movie)
    data["format"] = VERSION
    return data


def _read_kv(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise ValueError("private trace metadata missing or linked")
    result: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        key, sep, value = line.partition("=")
        if not sep or not key or not value or key in result:
            raise ValueError("private trace metadata malformed")
        result[key] = value
    return result


def _read_tsv(path: Path, fields: list[str]) -> list[dict[str, str]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("private trace artifact missing or linked")
    if path.stat().st_size > MAX_EVENT_BYTES:
        raise ValueError("private trace artifact exceeds conservative size limit")
    with path.open("r", encoding="ascii", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != fields:
            raise ValueError("private trace schema mismatch")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("private trace row is truncated")
    return rows


def _capture_digest_payload(before: dict, artifacts: dict[str, str]) -> bytes:
    canonical = {
        "format": VERSION,
        "rom_sha256": before["rom_sha256"],
        "fm2_sha256": before["fm2_sha256"],
        "artifact_sha256": artifacts,
    }
    return json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("ascii")


def preflight_trace(rom: Path, movie: Path, output: Path) -> dict:
    root = private_dir(output, require_empty=True)
    before = _identity(rom, movie)
    _create_json(root / PRE, before)
    return before


def _preflight_matches(rom: Path, movie: Path, output: Path) -> dict:
    root = private_dir(output)
    before = _json(root / PRE, PRE_FIELDS)
    if (
        before["format"] != VERSION
        or before["movie_power_on"] is not True
        or type(before["movie_frames"]) is not int
        or before["movie_frames"] <= 920
    ):
        raise ValueError("private PPU latch source preflight invalid")
    fresh = _identity(rom, movie)
    if fresh != before:
        raise ValueError("source ROM/FM2 identity changed")
    return before


def validate_trace_bundle(
    directory: Path,
    expected_writer_values: dict[int, list[int]] | None = None,
) -> dict:
    """Validate raw trace structure and reconstruct the shared PPU write latch."""
    root = private_dir(directory)
    complete = _read_kv(root / "COMPLETE.txt")
    counts_file = _read_kv(root / "ppu_register_counts.tsv")
    if set(complete) != COMPLETE_KEYS or set(counts_file) != COUNT_KEYS:
        raise ValueError("private PPU latch metadata schema mismatch")
    if (
        complete["format"] != "private_ppu_latch_trace_v1"
        or complete["frames"] != "321"
        or complete["frame_clock_rows"] != "321"
        or complete["rom_identity_verified"] != "yes"
        or complete["movie_readonly_verified"] != "yes"
        or counts_file["frames"] != "321"
        or counts_file["first"] != "600"
        or counts_file["last"] != "920"
        or counts_file["frame_clock_rows"] != "321"
        or counts_file["source_values_disclosed"] != "no"
    ):
        raise ValueError("private PPU latch completion witness invalid")

    event_path = root / "ppu_register_events.tsv"
    if event_path.is_symlink() or not event_path.is_file() or event_path.stat().st_size > MAX_EVENT_BYTES:
        raise ValueError("private PPU event trace missing or too large")
    events_raw = _read_tsv(event_path, EVENT_FIELDS)
    clocks_raw = _read_tsv(root / "ppu_register_frame_clock.tsv", CLOCK_FIELDS)
    if len(clocks_raw) != 321 or not events_raw or len(events_raw) > 200_000:
        raise ValueError("private PPU event/frame-clock coverage incomplete")

    clocks: dict[int, tuple[int, int]] = {}
    previous_end = None
    for index, row in enumerate(clocks_raw):
        frame = int(row["frame"])
        begin = int(row["begin_cycle"])
        end = int(row["end_cycle"])
        if frame != 600 + index or end <= begin or not 25_000 <= end - begin <= 40_000:
            raise ValueError("private PPU frame clock is malformed")
        if previous_end is not None and begin != previous_end:
            raise ValueError("private PPU frame clock has a gap or overlap")
        clocks[frame] = (begin, end)
        previous_end = end

    allowed_types = set(COUNT_TYPES)
    events: list[dict] = []
    actual_counts: Counter = Counter()
    last_frame = 600
    last_cycle = -1
    address_for_type = {
        "W2000": 0x2000, "W2001": 0x2001, "W2002": 0x2002,
        "W2005": 0x2005, "W2006": 0x2006, "R2002": 0x2002,
    }
    for expected_seq, row in enumerate(events_raw, 1):
        try:
            event = {
                "frame": int(row["frame"]),
                "seq": int(row["seq"]),
                "type": row["type"],
                "address": int(row["address"], 16),
                "size": int(row["size"]),
                "value": row["value"],
                "pc": int(row["pc"], 16),
                "opcode": int(row["opcode"], 16),
                "a": int(row["a"], 16),
                "x": int(row["x"], 16),
                "y": int(row["y"], 16),
                "cycle": int(row["cycle"]),
            }
        except (TypeError, ValueError) as exc:
            raise ValueError("private PPU event contains an invalid field") from exc
        frame = event["frame"]
        if (
            event["seq"] != expected_seq
            or event["type"] not in allowed_types
            or frame not in clocks
            or frame < last_frame
            or event["cycle"] < last_cycle
            or event["size"] != 1
            or event["address"] != address_for_type[event["type"]]
        ):
            raise ValueError("private PPU event order/address invalid")
        begin, end = clocks[frame]
        if not begin <= event["cycle"] <= end:
            raise ValueError("private PPU event lies outside its source frame")
        if event["type"] == "R2002":
            if (
                event["value"] != "--"
                or event["pc"] not in READ_PCS
                or event["opcode"] not in {0x19, 0x1F, 0x2C, 0xAD, 0xCE, 0xDD}
                or (event["opcode"] == 0x19 and event["y"] != 0)
                or (event["opcode"] in {0x1F, 0xDD} and event["x"] != 0)
            ):
                raise ValueError("PPUSTATUS read candidate was not verified against the live opcode")
        else:
            if not re.fullmatch(r"[0-9A-F]{2}", event["value"]) or event["opcode"] != 0:
                raise ValueError("private PPU write value/schema invalid")
        actual_counts[event["type"]] += 1
        events.append(event)
        last_frame = frame
        last_cycle = event["cycle"]

    actual_counts_full = {kind: actual_counts.get(kind, 0) for kind in COUNT_TYPES}
    if (
        int(complete["events"]) != len(events)
        or int(counts_file["total_events"]) != len(events)
        or any(int(counts_file[kind]) != actual_counts_full[kind] for kind in COUNT_TYPES)
    ):
        raise ValueError("private PPU event totals do not match the completion witness")

    by_frame: dict[int, list[dict]] = defaultdict(list)
    for event in events:
        by_frame[event["frame"]].append(event)
    roles: dict[int, list[int]] = defaultdict(list)
    state = None
    for event in events:
        if event["type"] == "R2002":
            state = 0
        elif event["type"] in {"W2005", "W2006"}:
            if event["type"] == "W2005":
                if state is None:
                    raise ValueError("PPU write latch state is unknown at a scroll write")
                roles[event["frame"]].append(state)
            if state is not None:
                state = 1 - state

    interrupted_pairs = 0
    for frame in range(600, 921):
        rows = by_frame[frame]
        scroll = [event for event in rows if event["type"] == "W2005"]
        if len(scroll) != 4:
            raise ValueError("original route must have four PPU scroll writes per frame")
        if [event["pc"] for event in scroll] != list(WRITE_PC_AFTER):
            raise ValueError("PPU scroll writer instruction sequence changed")
        values = [int(event["value"], 16) for event in scroll]
        if values[0] != 0 or values[2:] != [0, 0]:
            raise ValueError("PPU scroll writer value pattern changed")
        if roles.get(frame) != [0, 1, 0, 1]:
            raise ValueError("shared PPU scroll/address latch roles changed")
        scroll_indices = [i for i, event in enumerate(rows) if event["type"] == "W2005"]
        for left, right in zip(scroll_indices, scroll_indices[1:]):
            if any(event["type"] in {"R2002", "W2006"} for event in rows[left + 1:right]):
                interrupted_pairs += 1
    if interrupted_pairs:
        raise ValueError("PPU scroll pair interrupted by a direct status read or address write")

    if expected_writer_values is not None:
        if set(expected_writer_values) != set(range(600, 921)):
            raise ValueError("reference CPU writer trace does not cover all 321 frames")
        matched = 0
        for frame in range(600, 921):
            actual = [int(event["value"], 16) for event in by_frame[frame] if event["type"] == "W2005"]
            if actual != expected_writer_values[frame]:
                raise ValueError("actual PPU port values differ from the sealed CPU writer trace")
            matched += len(actual)
        if matched != 1284:
            raise ValueError("PPU/CPU writer cross-check incomplete")
    else:
        matched = 0

    return {
        "frames": 321,
        "events": len(events),
        "counts": actual_counts_full,
        "scroll_writes": 1284,
        "status_read_candidates": actual_counts_full["R2002"],
        "scroll_latch_roles_per_frame": "0,1,0,1",
        "interrupted_scroll_pairs": interrupted_pairs,
        "cpu_port_values_matched": matched,
        "raw_values_disclosed": False,
    }


def finalize_trace(rom: Path, movie: Path, output: Path) -> dict:
    root = private_dir(output)
    before = _preflight_matches(rom, movie, root)
    summary = validate_trace_bundle(root)
    hashes = {name: sha256_file(root / name) for name in ARTIFACTS}
    if _preflight_matches(rom, movie, root) != before:
        raise ValueError("source ROM/FM2 changed during private trace sealing")
    sealed = {
        "format": VERSION,
        "rom_sha256": before["rom_sha256"],
        "fm2_sha256": before["fm2_sha256"],
        "artifact_sha256": hashes,
        "content_seal_sha256": hashlib.sha256(
            _capture_digest_payload(before, hashes)
        ).hexdigest(),
        "capture_completed": True,
    }
    _create_json(root / POST, sealed)
    return summary


def verify_trace_seal(rom: Path, movie: Path, output: Path) -> dict:
    root = private_dir(output)
    before = _preflight_matches(rom, movie, root)
    sealed = _json(root / POST, POST_FIELDS)
    if (
        sealed["format"] != VERSION
        or sealed["rom_sha256"] != before["rom_sha256"]
        or sealed["fm2_sha256"] != before["fm2_sha256"]
        or sealed["capture_completed"] is not True
        or type(sealed["artifact_sha256"]) is not dict
        or set(sealed["artifact_sha256"]) != set(ARTIFACTS)
    ):
        raise ValueError("private PPU latch source-to-capture seal invalid")
    hashes = {name: sha256_file(root / name) for name in ARTIFACTS}
    if hashes != sealed["artifact_sha256"]:
        raise ValueError("private PPU latch evidence changed after sealing")
    digest = hashlib.sha256(_capture_digest_payload(before, hashes)).hexdigest()
    if sealed["content_seal_sha256"] != digest:
        raise ValueError("private PPU latch content seal checksum mismatch")
    validate_trace_bundle(root)
    if _preflight_matches(rom, movie, root) != before:
        raise ValueError("source ROM/FM2 changed during private trace verification")
    return before


def _reference_writer_values(capture_dir: Path) -> dict[int, list[int]]:
    path = capture_dir / "road_321_writers.tsv"
    rows = _read_tsv(path, ["frame", "ordinal", "pc", "value", "cycle"])
    if len(rows) != 1284:
        raise ValueError("sealed reference CPU writer trace is incomplete")
    result: dict[int, list[int]] = {}
    for frame in range(600, 921):
        selected = [row for row in rows if int(row["frame"]) == frame]
        if [int(row["ordinal"]) for row in selected] != [1, 2, 3, 4]:
            raise ValueError("sealed reference CPU writer frame/order mismatch")
        result[frame] = [int(row["value"], 16) for row in selected]
    return result


def audit(rom: Path, movie: Path, trace_dir: Path, reference_capture: Path) -> dict:
    trace_root = private_dir(trace_dir)
    reference_root = private_dir(reference_capture)
    identity = verify_trace_seal(rom, movie, trace_root)
    reference_summary = verify_source_capture(rom, movie, reference_root)
    if (
        reference_summary.get("full_ppu_writer_phase_frame_coverage") != 321
        or reference_summary.get("source_cpu_events_verified") != 1284
    ):
        raise ValueError("sealed reference source capture is incomplete")
    reference_identity = _json(reference_root / REFERENCE_PRE, REFERENCE_PRE_FIELDS)
    if (
        identity["rom_sha256"] != reference_identity["rom_sha256"]
        or identity["fm2_sha256"] != reference_identity["fm2_sha256"]
        or identity["rom_payload_md5"] != reference_identity["rom_payload_md5"]
        or identity["movie_frames"] != reference_identity["movie_frames"]
        or identity["movie_power_on"] is not True
    ):
        raise ValueError("PPU latch trace and reference capture source identities differ")

    expected = _reference_writer_values(reference_root)
    summary = validate_trace_bundle(trace_root, expected)
    if summary["counts"] != EXPECTED_ORIGINAL_COUNTS:
        raise ValueError("original-source PPU access count signature changed")
    return {
        "frames": summary["frames"],
        "events": summary["events"],
        "direct_status_read_candidates": summary["status_read_candidates"],
        "ppuctrl_writes": summary["counts"]["W2000"],
        "ppumask_writes": summary["counts"]["W2001"],
        "ppustatus_writes": summary["counts"]["W2002"],
        "scroll_writes": summary["scroll_writes"],
        "ppuaddr_writes": summary["counts"]["W2006"],
        "cpu_port_values_matched": summary["cpu_port_values_matched"],
        "latch_roles_per_frame": summary["scroll_latch_roles_per_frame"],
        "interrupted_scroll_pairs": summary["interrupted_scroll_pairs"],
        "source_identity_matches_reference": True,
        "raw_values_disclosed": False,
        "effective_ppu_scroll_proven": False,
        "camera_speed_proven": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--movie", required=True, type=Path)
    parser.add_argument("--trace-dir", required=True, type=Path)
    parser.add_argument("--reference-capture", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.rom, args.movie, args.trace_dir, args.reference_capture)
    print(
        "VPD_PRIVATE_PPU_REGISTER_LATCH_PASS"
        f" frames={result['frames']}"
        f" direct_status_read_candidates={result['direct_status_read_candidates']}"
        f" ppuctrl_writes={result['ppuctrl_writes']}"
        f" ppumask_writes={result['ppumask_writes']}"
        f" ppustatus_writes={result['ppustatus_writes']}"
        f" scroll_writes={result['scroll_writes']}"
        f" ppuaddr_writes={result['ppuaddr_writes']}"
        f" cpu_port_values_matched={result['cpu_port_values_matched']}"
        " latch_roles=0,1,0,1_per_frame"
        f" interrupted_scroll_pairs={result['interrupted_scroll_pairs']}"
        " source_identity_matches_reference=yes raw_values_disclosed=no"
        " effective_scroll_proven=no camera_speed_proven=no"
    )


if __name__ == "__main__":
    main()
