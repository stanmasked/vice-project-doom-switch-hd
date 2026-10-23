#!/usr/bin/env python3
"""Seal and audit one private FCEUX session joining PPU, CPU, RAM and RGB evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from seal_private_road_ppu_321 import (
    _create_json,
    _json,
    private_dir,
    sha256_file,
    source_identity,
)

PRE = "SOURCE_IDENTITY_BEFORE.json"
POST = "SOURCE_IDENTITY_SEALED.json"
VERSION = "vpd-private-road-ppu-latch-rgb321-identity-v1"
ARTIFACTS = (
    "road_321_writers.tsv",
    "road_321_postframe.tsv",
    "source_frame_clock.tsv",
    "road_321_rgb_scanlines.bin",
    "ppu_register_events.tsv",
    "ppu_register_counts.tsv",
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
WRITER_FIELDS = ["frame", "ordinal", "pc", "value", "cycle"]
RAM_FIELDS = ["frame", "ram_0d", "ppu_2005_writes"]
COUNT_TYPES = ("R2002", "W2000", "W2001", "W2002", "W2005", "W2006")
COUNT_KEYS = {
    "frames", "first", "last", *COUNT_TYPES, "frame_clock_rows",
    "total_events", "cpu_writer_events", "postframe_ram_samples",
    "rgb_slots", "source_values_disclosed",
}
COMPLETE = {
    "format": "private_road_ppu_latch_rgb321_v1",
    "frames": "321",
    "events": "10203",
    "frame_clock_rows": "321",
    "cpu_writer_events": "1284",
    "postframe_ram_samples": "321",
    "rgb_slots": "41",
    "rom_identity_verified": "yes",
    "movie_readonly_verified": "yes",
    "source_values_disclosed": "no",
}
EXPECTED_COUNTS = {
    "R2002": 845,
    "W2000": 808,
    "W2001": 642,
    "W2002": 0,
    "W2005": 1284,
    "W2006": 6624,
}
SLOT_BASES = (0x8000, 0xA000, 0xC000, 0xE000)
READ_OFFSETS = (
    0x001E, 0x1EA8, 0x03AC, 0x03B1, 0x03C7, 0x062E, 0x0659,
    0x069A, 0x070E, 0x072E, 0x08E7, 0x0923, 0x0928,
    0x1218, 0x1434, 0x1522, 0x1D01,
)
READ_PCS = {base + offset for base in SLOT_BASES for offset in READ_OFFSETS}
WRITER_PC_BEFORE = (0xE8EC, 0xE8F1, 0xE369, 0xE36C)
WRITER_PC_AFTER = (0xE8EF, 0xE8F4, 0xE36C, 0xE36F)
MAX_FILE_BYTES = 100_000_000


def _identity(rom: Path, movie: Path) -> dict:
    data = source_identity(rom, movie)
    data["format"] = VERSION
    return data


def _read_kv(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise ValueError("private capture metadata missing, linked, or too large")
    result: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        key, sep, value = line.partition("=")
        if not sep or not key or not value or key in result:
            raise ValueError("private capture metadata malformed")
        result[key] = value
    return result


def _read_tsv(path: Path, fields: list[str]) -> list[dict[str, str]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("private capture TSV missing, linked, or too large")
    with path.open("r", encoding="ascii", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != fields:
            raise ValueError("private capture TSV schema mismatch")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("private capture TSV contains a truncated row")
    return rows


def _capture_digest_payload(before: dict, artifacts: dict[str, str]) -> bytes:
    canonical = {
        "format": VERSION,
        "rom_sha256": before["rom_sha256"],
        "fm2_sha256": before["fm2_sha256"],
        "artifact_sha256": artifacts,
    }
    return json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("ascii")


def validate_capture(directory: Path) -> dict:
    """Validate a synthetic or owner-private combined capture without exposing its data."""
    root = private_dir(directory)
    complete = _read_kv(root / "COMPLETE.txt")
    if complete != COMPLETE:
        raise ValueError("same-session capture completion witness mismatch")

    counts_file = _read_kv(root / "ppu_register_counts.tsv")
    if set(counts_file) != COUNT_KEYS:
        raise ValueError("same-session PPU count schema mismatch")
    expected_meta = {
        "frames": "321",
        "first": "600",
        "last": "920",
        "frame_clock_rows": "321",
        "total_events": "10203",
        "cpu_writer_events": "1284",
        "postframe_ram_samples": "321",
        "rgb_slots": "41",
        "source_values_disclosed": "no",
        **{kind: str(count) for kind, count in EXPECTED_COUNTS.items()},
    }
    if counts_file != expected_meta:
        raise ValueError("same-session PPU count totals mismatch")

    clocks_raw = _read_tsv(root / "source_frame_clock.tsv", CLOCK_FIELDS)
    if len(clocks_raw) != 321:
        raise ValueError("same-session frame-clock coverage incomplete")
    clocks: dict[int, tuple[int, int]] = {}
    previous_end = None
    max_boundary_gap = 0
    for index, row in enumerate(clocks_raw):
        try:
            frame, begin, end = int(row["frame"]), int(row["begin_cycle"]), int(row["end_cycle"])
        except ValueError as exc:
            raise ValueError("same-session frame clock contains invalid numbers") from exc
        if frame != 600 + index or end <= begin or not 25_000 <= end - begin <= 40_000:
            raise ValueError("same-session frame clock is malformed")
        if previous_end is not None:
            gap = begin - previous_end
            max_boundary_gap = max(max_boundary_gap, gap)
            if gap < 0 or gap > 64:
                raise ValueError("same-session frame clock has a gap or overlap")
        clocks[frame] = (begin, end)
        previous_end = end

    events_raw = _read_tsv(root / "ppu_register_events.tsv", EVENT_FIELDS)
    if len(events_raw) != 10203:
        raise ValueError("same-session PPU event coverage incomplete")
    address_for_type = {
        "R2002": 0x2002, "W2000": 0x2000, "W2001": 0x2001,
        "W2002": 0x2002, "W2005": 0x2005, "W2006": 0x2006,
    }
    allowed_types = set(COUNT_TYPES)
    counts: Counter = Counter()
    by_frame: dict[int, list[dict]] = defaultdict(list)
    events: list[dict] = []
    last_frame, last_cycle = 600, -1
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
            raise ValueError("same-session PPU event contains an invalid field") from exc
        frame = event["frame"]
        if (
            event["seq"] != expected_seq
            or event["type"] not in allowed_types
            or event["address"] != address_for_type[event["type"]]
            or event["size"] != 1
            or frame not in clocks
            or frame < last_frame
            or event["cycle"] < last_cycle
        ):
            raise ValueError("same-session PPU event order/address invalid")
        begin, end = clocks[frame]
        if not begin <= event["cycle"] <= end:
            raise ValueError("same-session PPU event lies outside its frame clock")
        if event["type"] == "R2002":
            if (
                event["value"] != "--"
                or event["pc"] not in READ_PCS
                or event["opcode"] not in {0x19, 0x1F, 0x2C, 0xAD, 0xCE, 0xDD}
                or (event["opcode"] == 0x19 and event["y"] != 0)
                or (event["opcode"] in {0x1F, 0xDD} and event["x"] != 0)
            ):
                raise ValueError("PPUSTATUS read candidate does not match the live instruction")
        elif not re.fullmatch(r"[0-9A-F]{2}", event["value"]) or event["opcode"] != 0:
            raise ValueError("same-session PPU write value/schema invalid")
        counts[event["type"]] += 1
        by_frame[frame].append(event)
        events.append(event)
        last_frame, last_cycle = frame, event["cycle"]

    actual_counts = {kind: counts.get(kind, 0) for kind in COUNT_TYPES}
    if actual_counts != EXPECTED_COUNTS:
        raise ValueError("same-session PPU event counts do not match the declared totals")

    cpu_raw = _read_tsv(root / "road_321_writers.tsv", WRITER_FIELDS)
    if len(cpu_raw) != 1284:
        raise ValueError("same-session CPU writer trace incomplete")
    cpu_by_frame: dict[int, list[dict]] = defaultdict(list)
    for row in cpu_raw:
        try:
            frame = int(row["frame"])
            ordinal = int(row["ordinal"])
            pc = int(row["pc"], 16)
            value = int(row["value"], 16)
            cycle = int(row["cycle"])
        except ValueError as exc:
            raise ValueError("same-session CPU writer trace contains invalid numbers") from exc
        if (
            frame not in clocks or not 1 <= ordinal <= 4 or not 0 <= value <= 255
            or not re.fullmatch(r"[0-9A-F]{4}", row["pc"])
            or not re.fullmatch(r"[0-9A-F]{2}", row["value"])
        ):
            raise ValueError("same-session CPU writer row is outside the capture contract")
        begin, end = clocks[frame]
        if not begin <= cycle <= end:
            raise ValueError("same-session CPU writer lies outside its frame clock")
        cpu_by_frame[frame].append({
            "ordinal": ordinal, "pc": pc, "value": value, "cycle": cycle,
        })

    interrupted_pairs = 0
    for frame in range(600, 921):
        cpu = cpu_by_frame[frame]
        scroll = [event for event in by_frame[frame] if event["type"] == "W2005"]
        if (
            len(cpu) != 4
            or [row["ordinal"] for row in cpu] != [1, 2, 3, 4]
            or [row["pc"] for row in cpu] != list(WRITER_PC_BEFORE)
            or len(scroll) != 4
            or [event["pc"] for event in scroll] != list(WRITER_PC_AFTER)
        ):
            raise ValueError("same-session CPU/PPU writer sequence mismatch")
        cpu_values = [row["value"] for row in cpu]
        ppu_values = [int(event["value"], 16) for event in scroll]
        cpu_cycles = [row["cycle"] for row in cpu]
        ppu_cycles = [event["cycle"] for event in scroll]
        if (
            cpu_values != ppu_values
            or cpu_cycles != ppu_cycles
            or cpu_values[0] != 0
            or cpu_values[2:] != [0, 0]
            or cpu_cycles[1] - cpu_cycles[0] != 7
            or cpu_cycles[3] - cpu_cycles[2] != 4
            or not (cpu_cycles[0] <= cpu_cycles[1] < cpu_cycles[2] <= cpu_cycles[3])
        ):
            raise ValueError("same-session CPU instruction and actual PPU bus writes differ")
        indices = [i for i, event in enumerate(by_frame[frame]) if event["type"] == "W2005"]
        for left, right in zip(indices, indices[1:]):
            if any(event["type"] in {"R2002", "W2006"} for event in by_frame[frame][left + 1:right]):
                interrupted_pairs += 1
    if interrupted_pairs:
        raise ValueError("a PPUSTATUS candidate or PPUADDR write interrupts a scroll-write pair")

    state = None
    latch_roles: dict[int, list[int]] = defaultdict(list)
    for event in events:
        if event["type"] == "R2002":
            state = 0
        elif event["type"] in {"W2005", "W2006"}:
            if event["type"] == "W2005":
                if state is None:
                    raise ValueError("PPU write-toggle state is unknown at a scroll write")
                latch_roles[event["frame"]].append(state)
            if state is not None:
                state = 1 - state
    if any(latch_roles[frame] != [0, 1, 0, 1] for frame in range(600, 921)):
        raise ValueError("shared PPUSCROLL/PPUADDR write-toggle roles changed")

    ram_raw = _read_tsv(root / "road_321_postframe.tsv", RAM_FIELDS)
    if len(ram_raw) != 321:
        raise ValueError("same-session postframe RAM coverage incomplete")
    for index, row in enumerate(ram_raw):
        if (
            int(row["frame"]) != 600 + index
            or not re.fullmatch(r"[0-9A-F]{2}", row["ram_0d"])
            or row["ppu_2005_writes"] != "4"
        ):
            raise ValueError("same-session postframe RAM sample malformed")

    rgb_path = root / "road_321_rgb_scanlines.bin"
    if rgb_path.is_symlink() or not rgb_path.is_file() or rgb_path.stat().st_size != 126054:
        raise ValueError("same-session RGB scanline capture missing or malformed")
    rgb = rgb_path.read_bytes()
    if rgb[:8] != b"VPDRGB41" or rgb[8:20] != bytes((41, 0, 0, 1, 4, 0, 0, 0, 120, 140, 160, 180)):
        raise ValueError("same-session RGB scanline header mismatch")
    offset = 20
    for frame in range(600, 921, 8):
        if rgb[offset:offset + 2] != bytes((frame % 256, frame // 256)):
            raise ValueError("same-session RGB slot frame order mismatch")
        offset += 3074
    if offset != len(rgb):
        raise ValueError("same-session RGB scanline payload length mismatch")

    return {
        "frames": 321,
        "cpu_writer_events": 1284,
        "ppu_register_events": len(events),
        "postframe_ram_samples": len(ram_raw),
        "rgb_slots": 41,
        "cpu_port_values_matched": 1284,
        "cpu_port_cycles_matched": 1284,
        "direct_status_read_candidates": actual_counts["R2002"],
        "ppuctrl_writes": actual_counts["W2000"],
        "ppumask_writes": actual_counts["W2001"],
        "ppustatus_writes": actual_counts["W2002"],
        "scroll_writes": actual_counts["W2005"],
        "ppuaddr_writes": actual_counts["W2006"],
        "latch_roles_per_frame": "0,1,0,1",
        "interrupted_scroll_pairs": interrupted_pairs,
        "max_boundary_gap_cycles": max_boundary_gap,
        "same_session_cpu_ram_ppu_rgb_joined": True,
        "raw_source_values_disclosed": False,
        "effective_ppu_scroll_proven": False,
        "camera_speed_proven": False,
        "collision_geometry_proven": False,
    }


def preflight(rom: Path, movie: Path, output: Path) -> dict:
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
        raise ValueError("same-session source preflight invalid")
    fresh = _identity(rom, movie)
    if fresh != before:
        raise ValueError("source ROM/FM2 identity changed")
    return before


def finalize(rom: Path, movie: Path, output: Path) -> dict:
    root = private_dir(output)
    before = _preflight_matches(rom, movie, root)
    summary = validate_capture(root)
    hashes = {name: sha256_file(root / name) for name in ARTIFACTS}
    if _preflight_matches(rom, movie, root) != before:
        raise ValueError("source ROM/FM2 changed during same-session sealing")
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


def verify(rom: Path, movie: Path, output: Path) -> dict:
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
        raise ValueError("same-session source-to-capture seal invalid")
    hashes = {name: sha256_file(root / name) for name in ARTIFACTS}
    if hashes != sealed["artifact_sha256"]:
        raise ValueError("same-session capture artifact changed after sealing")
    digest = hashlib.sha256(_capture_digest_payload(before, hashes)).hexdigest()
    if sealed["content_seal_sha256"] != digest:
        raise ValueError("same-session capture content seal checksum mismatch")
    summary = validate_capture(root)
    if _preflight_matches(rom, movie, root) != before:
        raise ValueError("source ROM/FM2 changed during same-session verification")
    return {
        **summary,
        "original_source_full_file_sha256_stable": True,
        "source_fm2_matching_cartridge_payload_md5": True,
        "source_fm2_power_on_preflight": True,
        "capture_artifacts_sealed": True,
        "original_assets_in_public_report": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "finalize", "verify"))
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--movie", required=True, type=Path)
    parser.add_argument("--capture-dir", required=True, type=Path)
    args = parser.parse_args()
    action = {"preflight": preflight, "finalize": finalize, "verify": verify}[args.action]
    action(args.rom, args.movie, args.capture_dir)
    print(
        f"VPD_PRIVATE_ROAD_PPU_LATCH_RGB321_{args.action.upper()}_PASS"
        " source_identity_private=yes raw_source_values_disclosed=no"
        " effective_ppu_scroll_proven=no"
    )


if __name__ == "__main__":
    main()
