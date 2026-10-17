#!/usr/bin/env python3
"""Stage114: classify and bound native low/high CHR plane pairs for MMC3 ROMs."""
import argparse
import re
import tempfile
from pathlib import Path

from make_stage110_synthetic_midframe_rom import make_rom
from run_stage111_native_tile_boundary import run_native
from run_stage112_native_subscanline_sweep import PHASES, validate_sweep
from run_stage113_native_prefetch import verify_report as verify_prefetch

MARKER = "VPD_STAGE114_NATIVE_PLANE_PAIR_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE114_NATIVE_PLANE_PAIR_PASS "
    r"switch_sl=(\d+) old_tiles=128 new_tiles=128 "
    r"mixed_pairs=0 writes_between_planes=0 "
    r"low_to_high_min=(\d+) low_to_high_max=(\d+) "
    r"source_clock_only=yes pinned_fceux_only=yes "
    r"synthetic_only=yes original_game_mixed_tiles_proven=no$", re.MULTILINE,
)


class PlaneAuditError(ValueError):
    pass


def verify_report(log, tile, prefetch):
    matches = list(PATTERN.finditer(log))
    if len(matches) != 1 or log.count(MARKER) != 1:
        raise PlaneAuditError("Missing/forged or duplicated plane-pair native marker")
    source_line, low, high = map(int, matches[0].groups())
    if (source_line != tile["switch_source_scanline"] or
            source_line != prefetch["switch_source_scanline"] or
            tile["first_new_xt"] != prefetch["first_new_xt"] or
            not 1 <= low <= high <= 8 or
            not tile.get("same_buffered_tile_frame_proven") or
            prefetch.get("original_game_prefetch_proven") is not False):
        raise PlaneAuditError("Unbound plane-pair read/draw and original-game claims")
    return {"source_sl": source_line, "low_to_high_min_ticks": low,
            "low_to_high_max_ticks": high,
            "mixed_pairs_observed": 0,
            "writes_between_planes_observed": 0,
            "original_game_mixed_tiles_proven": False}


def run(binary, temp):
    with tempfile.TemporaryDirectory(dir=temp) as name:
        root = Path(name)
        observations = []
        for phase in PHASES:
            path = root / ("phase_%d.nes" % phase)
            make_rom(path, phase_nops=phase)
            tile, log = run_native(binary, path, root / ("observed_%d" % phase),
                                   prefetch=True, plane_pairs=True)
            prefetch = verify_prefetch(log, tile)
            pair = verify_report(log, tile, prefetch)
            observations.append((phase, tile, pair))
        fixed = root / "fixed.nes"
        make_rom(fixed, switch=False)
        run_native(binary, fixed, root / "fixed", positive=False,
                   prefetch=True, plane_pairs=True)
        run_native(binary, root / ("phase_%d.nes" % PHASES[-1]),
                   root / "disabled", enabled=False, positive=False,
                   prefetch=True, plane_pairs=True)
    sweep = validate_sweep([(phase, tile) for phase, tile, _ in observations])
    values = [pair for _, _, pair in observations]
    if (any(v["source_sl"] != sweep["switch_sl"] for v in values) or
            any(v["mixed_pairs_observed"] != 0 for v in values)):
        raise PlaneAuditError("Inconsistent synthetic plane classification across phases")
    print(
        "STAGE114_NATIVE_BG_PLANE_PAIR_PROOF native_fceux=yes "
        "synthetic_mapper4_only=yes phases=0,4,8,12 "
        "old_tiles_each=128 new_tiles_each=128 "
        "mixed_pairs_each=0 split_writes_each=0 "
        "low_to_high_min=%s low_to_high_max=%s "
        "all_phases_bound_to_native_prefetch_and_xbuf=yes "
        "fixed_bank_control=clean disabled_probe_control=clean "
        "nes_hardware_mixed_tiles_ruled_out=no original_game_mixed_tiles_proven=no" %
        (",".join(str(v["low_to_high_min_ticks"]) for v in values),
         ",".join(str(v["low_to_high_max_ticks"]) for v in values))
    )
    return sweep, values


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_fceux", type=Path)
    parser.add_argument("private_temp", type=Path)
    args = parser.parse_args()
    run(args.native_fceux, args.private_temp)
