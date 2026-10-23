#!/usr/bin/env python3
"""Audit and seal the same-session source writes to NES zero-page RAM $0D."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from audit_private_road_ppu_latch_rgb321 import (
    PRE, POST, PRE_FIELDS, verify as verify_base_capture,
)
from seal_private_road_321 import _create_json, _json, private_dir, sha256_file

TRACE_VERSION = "vpd-private-ram0d-scroll-writer-seal-v1"
TRACE_COMPLETE = "RAM0D_TRACE_COMPLETE.txt"
TRACE_ROWS = "road_321_ram_writes.tsv"
TRACE_SEAL = "RAM0D_TRACE_SEAL.json"
TRACE_FIELDS = [
    "frame", "pc_after", "cycle", "old_value", "new_value",
    "a", "x", "y", "prev", "opcode", "operand",
]
CLOCK_FIELDS = ["frame", "begin_cycle", "end_cycle"]
WRITER_FIELDS = ["frame", "ordinal", "pc", "value", "cycle"]
RAM_FIELDS = ["frame", "ram_0d", "ppu_2005_writes"]
TRACE_SEAL_FIELDS = {
    "format", "rom_sha256", "fm2_sha256", "base_capture_seal_sha256",
    "artifact_sha256", "content_seal_sha256", "capture_completed",
}
TRACE_ARTIFACTS = (TRACE_ROWS, TRACE_COMPLETE)
EXPECTED_WRITER_PCS = ("E8EC", "E8F1", "E369", "E36C")
EXPECTED_COMPLETE = {
    "format": "private_ram0d_scroll_writer_trace_v1",
    "frames": "321",
    "ram0d_write_events": "1506",
    "ram0d_dec_events": "1500",
    "ram0d_sta_events": "6",
    "writer_prev_frame_comparisons": "320",
    "writer_prev_frame_matches": "319",
    "writer_prev_frame_mismatches": "1",
    "writer_prev_frame_first_mismatch": "601",
    "source_values_disclosed": "no",
}
EXPECTED_WRITE_DISTRIBUTION = {
    0: 13, 1: 2, 2: 7, 3: 4, 4: 6, 5: 282, 6: 6, 8: 1,
}
MAX_FILE_BYTES = 100_000_000


def _read_kv(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise ValueError("private RAM trace completion marker missing, linked, or oversized")
    result: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or not value or key in result:
            raise ValueError("private RAM trace completion marker malformed")
        result[key] = value
    return result


def _read_tsv(path: Path, fields: list[str]) -> list[dict[str, str]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("private RAM trace file missing, linked, or oversized")
    with path.open("r", encoding="ascii", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != fields:
            raise ValueError("private RAM trace TSV schema mismatch")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("private RAM trace contains a truncated row")
    return rows


def validate_trace(directory: Path) -> dict:
    """Validate numeric RAM-write evidence without printing or exporting its values."""
    root = private_dir(directory)
    if _read_kv(root / TRACE_COMPLETE) != EXPECTED_COMPLETE:
        raise ValueError("same-session RAM $0D completion witness mismatch")

    clock_rows = _read_tsv(root / "source_frame_clock.tsv", CLOCK_FIELDS)
    if len(clock_rows) != 321:
        raise ValueError("same-session RAM trace frame clock incomplete")
    clocks: dict[int, tuple[int, int]] = {}
    previous_end = None
    for index, row in enumerate(clock_rows):
        try:
            frame = int(row["frame"])
            begin = int(row["begin_cycle"])
            end = int(row["end_cycle"])
        except ValueError as exc:
            raise ValueError("same-session RAM frame clock contains invalid numbers") from exc
        if frame != 600 + index or begin < 0 or end <= begin or not 25000 <= end - begin <= 40000:
            raise ValueError("same-session RAM frame clock malformed")
        if previous_end is not None and not 0 <= begin - previous_end <= 64:
            raise ValueError("same-session RAM frame clock gap or overlap")
        clocks[frame] = (begin, end)
        previous_end = end

    ram_rows = _read_tsv(root / "road_321_postframe.tsv", RAM_FIELDS)
    if len(ram_rows) != 321:
        raise ValueError("same-session postframe RAM samples incomplete")
    ram_by_frame: dict[int, int] = {}
    for index, row in enumerate(ram_rows):
        if (
            int(row["frame"]) != 600 + index
            or not re.fullmatch(r"[0-9A-F]{2}", row["ram_0d"])
            or row["ppu_2005_writes"] != "4"
        ):
            raise ValueError("same-session postframe RAM sample malformed")
        ram_by_frame[600 + index] = int(row["ram_0d"], 16)

    writer_rows = _read_tsv(root / "road_321_writers.tsv", WRITER_FIELDS)
    if len(writer_rows) != 1284:
        raise ValueError("same-session CPU writer trace incomplete")
    writers_by_frame: dict[int, list[dict]] = defaultdict(list)
    writer2: dict[int, int] = {}
    for row in writer_rows:
        try:
            frame = int(row["frame"])
            ordinal = int(row["ordinal"])
            value = int(row["value"], 16)
            cycle = int(row["cycle"])
        except ValueError as exc:
            raise ValueError("same-session CPU writer contains invalid numbers") from exc
        if (
            frame not in clocks or not 1 <= ordinal <= 4 or not 0 <= value <= 255
            or not re.fullmatch(r"[0-9A-F]{4}", row["pc"])
            or not re.fullmatch(r"[0-9A-F]{2}", row["value"])
        ):
            raise ValueError("same-session CPU writer row outside capture contract")
        begin, end = clocks[frame]
        if not begin <= cycle <= end:
            raise ValueError("same-session CPU writer outside frame clock")
        writers_by_frame[frame].append({
            "ordinal": ordinal, "pc": row["pc"], "value": value, "cycle": cycle,
        })
    for frame in range(600, 921):
        rows = writers_by_frame[frame]
        if (
            len(rows) != 4
            or [row["ordinal"] for row in rows] != [1, 2, 3, 4]
            or tuple(row["pc"] for row in rows) != EXPECTED_WRITER_PCS
        ):
            raise ValueError("same-session CPU writer instruction order changed")
        values = [row["value"] for row in rows]
        if values[0] != 0 or values[2:] != [0, 0]:
            raise ValueError("same-session CPU writer value pattern changed")
        writer2[frame] = values[1]

    trace_rows = _read_tsv(root / TRACE_ROWS, TRACE_FIELDS)
    if len(trace_rows) != 1506:
        raise ValueError("same-session RAM $0D write trace incomplete")
    writes_by_frame: dict[int, list[dict]] = defaultdict(list)
    opcode_counts: Counter = Counter()
    previous_cycle = -1
    for row in trace_rows:
        try:
            frame = int(row["frame"])
            cycle = int(row["cycle"])
            pc = int(row["pc_after"], 16)
            old = int(row["old_value"], 16)
            new = int(row["new_value"], 16)
            av = int(row["a"], 16)
            int(row["x"], 16)
            int(row["y"], 16)
            int(row["prev"], 16)
            opcode = int(row["opcode"], 16)
            operand = int(row["operand"], 16)
        except ValueError as exc:
            raise ValueError("same-session RAM write trace contains invalid fields") from exc
        if (
            frame not in clocks
            or not 0 <= old <= 255 or not 0 <= new <= 255
            or not re.fullmatch(r"[0-9A-F]{4}", row["pc_after"])
            or any(not re.fullmatch(r"[0-9A-F]{2}", row[key])
                   for key in ("old_value", "new_value", "a", "x", "y", "prev", "opcode", "operand"))
            or cycle < previous_cycle
        ):
            raise ValueError("same-session RAM write trace order or field schema invalid")
        begin, end = clocks[frame]
        if not begin <= cycle <= end:
            raise ValueError("same-session RAM write lies outside its frame clock")
        if operand != 0x0D:
            raise ValueError("RAM write instruction does not target zero-page $0D")
        if opcode == 0xC6 and pc == 0xD3CC:
            if new != (old - 1) % 256:
                raise ValueError("executed DEC $0D did not decrement the prior byte")
            opcode_counts["DEC"] += 1
        elif opcode == 0x85 and pc == 0xD3CA:
            if new != av:
                raise ValueError("executed STA $0D value differs from A")
            opcode_counts["STA"] += 1
        else:
            raise ValueError("unrecognized live CPU instruction wrote RAM $0D")
        writes_by_frame[frame].append({"old": old, "new": new, "cycle": cycle})
        previous_cycle = cycle

    if opcode_counts != Counter({"DEC": 1500, "STA": 6}):
        raise ValueError("same-session RAM $0D instruction totals changed")
    distribution = Counter(len(writes_by_frame[frame]) for frame in range(600, 921))
    if dict(distribution) != EXPECTED_WRITE_DISTRIBUTION:
        raise ValueError("same-session per-frame RAM write distribution changed")

    for frame in range(600, 921):
        rows = writes_by_frame[frame]
        if rows:
            if frame > 600 and rows[0]["old"] != ram_by_frame[frame - 1]:
                raise ValueError("first RAM write old value differs from previous frame sample")
            if any(left["new"] != right["old"] for left, right in zip(rows, rows[1:])):
                raise ValueError("same-frame RAM write old/new chain is broken")
            if rows[-1]["new"] != ram_by_frame[frame]:
                raise ValueError("last RAM write differs from postframe RAM sample")
        elif frame > 600 and ram_by_frame[frame] != ram_by_frame[frame - 1]:
            raise ValueError("RAM $0D changed in a frame with no captured write")

    mismatch_frames = [
        frame for frame in range(601, 921)
        if writer2[frame] != ram_by_frame[frame - 1]
    ]
    if mismatch_frames != [601]:
        raise ValueError("RAM $0D to next-frame second-$2005 relation changed")

    return {
        "frames": 321,
        "ram0d_write_events": len(trace_rows),
        "ram0d_dec_events": opcode_counts["DEC"],
        "ram0d_sta_events": opcode_counts["STA"],
        "frames_with_ram0d_writes": sum(bool(writes_by_frame[f]) for f in range(600, 921)),
        "writer_previous_frame_comparisons": 320,
        "writer_previous_frame_matches": 319,
        "writer_previous_frame_mismatches": 1,
        "first_mismatch_frame": 601,
        "per_frame_old_new_chain_verified": True,
        "instruction_pc_and_operand_verified": True,
        "same_session_rgb_cpu_ram_ppu_clock_joined": True,
        "ram0d_semantics_identified": False,
        "effective_ppu_scroll_proven": False,
        "camera_speed_proven": False,
        "collision_geometry_proven": False,
        "raw_source_values_disclosed": False,
    }


def _payload(before: dict, base_seal_sha256: str, artifacts: dict[str, str]) -> dict:
    return {
        "format": TRACE_VERSION,
        "rom_sha256": before["rom_sha256"],
        "fm2_sha256": before["fm2_sha256"],
        "base_capture_seal_sha256": base_seal_sha256,
        "artifact_sha256": artifacts,
    }


def _digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("ascii")).hexdigest()


def seal_trace(rom: Path, movie: Path, directory: Path) -> dict:
    root = private_dir(directory)
    base_summary = verify_base_capture(rom, movie, root)
    summary = validate_trace(root)
    before = _json(root / PRE, PRE_FIELDS)
    base_seal_sha256 = sha256_file(root / POST)
    hashes = {name: sha256_file(root / name) for name in TRACE_ARTIFACTS}
    if verify_base_capture(rom, movie, root) != base_summary:
        raise ValueError("source/base capture changed while sealing RAM trace")
    payload = _payload(before, base_seal_sha256, hashes)
    _create_json(root / TRACE_SEAL, {
        **payload,
        "content_seal_sha256": _digest(payload),
        "capture_completed": True,
    })
    return summary


def verify_trace(rom: Path, movie: Path, directory: Path) -> dict:
    root = private_dir(directory)
    base_summary = verify_base_capture(rom, movie, root)
    summary = validate_trace(root)
    before = _json(root / PRE, PRE_FIELDS)
    sealed = _json(root / TRACE_SEAL, TRACE_SEAL_FIELDS)
    expected_hashes = {name: sha256_file(root / name) for name in TRACE_ARTIFACTS}
    expected_payload = _payload(
        before, sha256_file(root / POST), expected_hashes,
    )
    if (
        sealed["format"] != TRACE_VERSION
        or sealed["rom_sha256"] != before["rom_sha256"]
        or sealed["fm2_sha256"] != before["fm2_sha256"]
        or sealed["base_capture_seal_sha256"] != expected_payload["base_capture_seal_sha256"]
        or sealed["artifact_sha256"] != expected_hashes
        or sealed["content_seal_sha256"] != _digest(expected_payload)
        or sealed["capture_completed"] is not True
    ):
        raise ValueError("same-session RAM trace source/content seal invalid")
    if verify_base_capture(rom, movie, root) != base_summary:
        raise ValueError("source/base capture changed during RAM trace verification")
    return {
        **base_summary,
        **summary,
        "ram0d_trace_sealed": True,
        "full_rom_fm2_identity_verified": True,
        "raw_source_values_disclosed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "seal", "verify"))
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--movie", type=Path)
    parser.add_argument("--capture-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.action == "validate":
            result = validate_trace(args.capture_dir)
        else:
            if args.rom is None or args.movie is None:
                parser.error("--rom and --movie are required for seal/verify")
            if args.action == "seal":
                seal_trace(args.rom, args.movie, args.capture_dir)
            result = verify_trace(args.rom, args.movie, args.capture_dir)
    except (OSError, ValueError, UnicodeError):
        parser.exit(1, "VPD_PRIVATE_RAM0D_TRACE_INCONCLUSIVE: validation failed; private evidence remains local\n")
    print(
        f"VPD_PRIVATE_RAM0D_SCROLL_RELATION_{args.action.upper()}_PASS"
        f" frames={result['frames']}"
        f" ram_writes={result['ram0d_write_events']}"
        f" dec={result['ram0d_dec_events']}"
        f" sta={result['ram0d_sta_events']}"
        f" previous_frame_matches={result['writer_previous_frame_matches']}/"
        f"{result['writer_previous_frame_comparisons']}"
        f" first_mismatch={result['first_mismatch_frame']}"
        " raw_values_disclosed=no ram0d_semantics_identified=no"
    )


if __name__ == "__main__":
    main()
