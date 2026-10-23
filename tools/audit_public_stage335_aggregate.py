#!/usr/bin/env python3
"""Validate only the redacted Stage 335 public aggregate; never reads private traces."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

SCHEMA = "vpd-stage335-public-aggregate-v1"
FORBIDDEN_KEYS = {
    "rom_sha256", "fm2_sha256", "rom_payload_md5", "source_hash",
    "file_id", "drive_file_id", "pc", "opcode", "operand", "address",
    "effective_address", "raw_bytes", "raw_trace", "source_path",
    "local_path", "source_values", "ram0d_value",
}

def _reject_private_fields(value, path="$"):
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9_]", "_", str(key).lower())
            if normalized in FORBIDDEN_KEYS:
                raise ValueError(f"private field is not allowed at {path}.{key}")
            _reject_private_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_private_fields(child, f"{path}[{index}]")

def audit_report(report: dict) -> dict:
    _reject_private_fields(report)
    expected_top = {
        "schema", "frame_window", "ppu_2005", "ppu_2006", "ppu_status",
        "ram_0d", "ppu_latch", "dataflow", "correlation",
        "interpretation", "privacy",
    }
    if set(report) != expected_top or report.get("schema") != SCHEMA:
        raise ValueError("public aggregate schema mismatch")
    if report["frame_window"] != {"frames": 261}:
        raise ValueError("frame window mismatch")

    ppu = report["ppu_2005"]
    if ppu != {"bus_writes": 1010, "matched_instruction_witnesses": 1010, "unmatched_writes": 0}:
        raise ValueError("PPU $2005 instruction-witness counts mismatch")
    if report["ppu_2006"] != {"bus_writes": 6096}:
        raise ValueError("PPU $2006 aggregate mismatch")
    if report["ppu_status"] != {"observed_reads": 10172}:
        raise ValueError("PPU status-read aggregate mismatch")

    ram = report["ram_0d"]
    if ram != {
        "writes": 619, "matched_instruction_witnesses": 619, "unmatched_writes": 0,
        "dec_writes": 615, "sta_writes": 4, "instruction_effect_mismatches": 0,
    }:
        raise ValueError("RAM $0D writer audit mismatch")

    latch = report["ppu_latch"]
    if latch != {
        "replay_mismatches": 0, "second_write_toggle_before": 1,
        "second_write_observations": 253, "second_write_toggle_mismatches": 0,
    }:
        raise ValueError("PPU write-toggle phase audit mismatch")

    dataflow = report["dataflow"]
    if set(dataflow) != {"ram_0b_load_to_first_2005_store", "ram_0d_load_to_second_2005_store"}:
        raise ValueError("dataflow schema mismatch")
    expected_pair = {"observations": 253, "matches": 253, "mismatches": 0}
    if dataflow["ram_0b_load_to_first_2005_store"] != expected_pair:
        raise ValueError("RAM $0B to first $2005 store counts mismatch")
    if dataflow["ram_0d_load_to_second_2005_store"] != {
        **expected_pair, "source_stable_until_store": True,
    }:
        raise ValueError("RAM $0D to second $2005 store counts mismatch")

    corr = report["correlation"]
    if corr != {
        "second_2005_current_ram_0d_comparisons": 253,
        "second_2005_current_ram_0d_matches": 253,
        "second_2005_current_ram_0d_mismatches": 0,
        "previous_frame_end_comparisons": 252,
        "previous_frame_end_matches": 251,
        "previous_frame_end_mismatches": 1,
        "intra_frame_writes_explain_previous_frame_difference": True,
    }:
        raise ValueError("RAM/PPU correlation aggregate mismatch")

    interp = report["interpretation"]
    if interp != {
        "ram_0d_loads_to_second_2005_store_in_observed_path": True,
        "second_2005_write_is_y_scroll_input": True,
        "effective_raster_scroll_proven": False,
        "camera_speed_proven": False,
        "road_geometry_proven": False,
        "collision_physics_proven": False,
    }:
        raise ValueError("interpretation limits mismatch")

    privacy = report["privacy"]
    if privacy != {
        "raw_trace_committed": False,
        "raw_values_disclosed": False,
        "source_hashes_disclosed": False,
        "instruction_sites_disclosed": False,
    }:
        raise ValueError("privacy contract mismatch")

    return {
        "frames": 261,
        "ppu_2005_writes": 1010,
        "ram_0d_writes": 619,
        "direct_load_store_pairs": 506,
        "second_write_live_ram_matches": 253,
        "raw_trace_committed": False,
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("docs/stage335_public_aggregate.json"))
    args = parser.parse_args()
    summary = audit_report(json.loads(args.input.read_text(encoding="utf-8")))
    print(
        "VPD_STAGE335_PUBLIC_AGGREGATE_PASS"
        f" frames={summary['frames']}"
        f" ppu2005={summary['ppu_2005_writes']}"
        f" ram0d={summary['ram_0d_writes']}"
        f" direct_pairs={summary['direct_load_store_pairs']}"
        f" live_matches={summary['second_write_live_ram_matches']}"
        " raw_private=yes"
    )

if __name__ == "__main__":
    main()
