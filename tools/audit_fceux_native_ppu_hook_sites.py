#!/usr/bin/env python3
"""Stage97 pinned upstream FCEUX PPU hook-site *source audit*, no patching.

The FCEUX "newppu" path and legacy PPU loop are separate implementations.
Presence of scanline/dot getters does not prove an NES raster contract.
"""
import argparse
import hashlib
import json
from pathlib import Path

FCEUX_REVISION = "8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8"
PPU_CPP_GIT_BLOB = "ce84a9df2c12b737fb13316737add1e9963a3ff7"
ANCHORS = {
    "newppu_scanline_getter": "int newppu_get_scanline() { return ppur.status.sl; }",
    "newppu_dot_getter": "int newppu_get_dot() { return ppur.status.cycle; }",
    "legacy_ppu_loop": "int FCEUPPU_Loop(int skip) {",
    "newppu_loop": "int FCEUX_PPU_Loop(int skip) {",
    "newppu_dispatch": "return FCEUX_PPU_Loop(skip);",
    "newppu_scanline_counter": "ppur.status.sl = sl;",
    "newppu_visible_y_adjustment": "const int yp = sl - 1;",
    "newppu_step_loop": "runppu(1);",
    "newppu_vblank_flag": "PPU_status |= 0x80;",
}
REQUIRED = frozenset(ANCHORS)


def git_blob_sha(content):
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def analyze_source(content, revision, *, exact_pinned_source=False):
    if not isinstance(content, bytes):
        raise TypeError("Expected original source bytes, not text")
    if revision != FCEUX_REVISION:
        raise ValueError("Unknown or unpinned upstream FCEUX revision")
    text = content.decode("utf8")
    found = {name: text.count(anchor) for name, anchor in ANCHORS.items()}
    if any(found[name] != 1 for name in REQUIRED if name not in (
        "newppu_step_loop", "newppu_vblank_flag")):
        raise ValueError("Missing/duplicate candidate native raster source anchor")
    for name in ("newppu_step_loop", "newppu_vblank_flag"):
        if found[name] < 1:
            raise ValueError("Missing candidate native raster source anchor")
    actual_blob = git_blob_sha(content)
    pinned = actual_blob == PPU_CPP_GIT_BLOB
    if exact_pinned_source and not pinned:
        raise ValueError("Source bytes are not the pinned upstream ppu.cpp blob")
    return {
        "format": "vpd_fceux_native_ppu_hook_site_audit_v1",
        "revision_declared": FCEUX_REVISION,
        "upstream_blob_matches_pinned_source": pinned,
        "candidate_newppu_getters_exist": True,
        "legacy_ppu_path_exists": True,
        "newppu_step_loop_exists": True,
        "visible_scanline_is_native_counter_minus_one": True,
        "newppu_and_legacy_paths_are_distinct": True,
        "safe_to_assume_native_counter_equals_nes_scanline": False,
        "timed_vblank_edges_independently_proven": False,
        "instrumentation_inserted_into_fceux": False,
        "source_build_compiled_or_emulator_executed": False,
        "original_game_geometry_reconstructed": False,
        "next_gate": "Review native tick-level hook after pinned source audit; account for PPU phase, odd frames and legacy fallback",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ppu_cpp", type=Path,
                        help="Local pinned upstream FCEUX src/ppu.cpp")
    parser.add_argument("--revision", default=FCEUX_REVISION)
    parser.add_argument("--require-exact-blob", action="store_true")
    args = parser.parse_args()
    print(json.dumps(analyze_source(
        args.ppu_cpp.read_bytes(), args.revision,
        exact_pinned_source=args.require_exact_blob),
        indent=2))


if __name__ == "__main__":
    main()
