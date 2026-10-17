#!/usr/bin/env python3
"""Correlate FCEUX end-of-line BGData lookahead with next-line XBuf pixels."""
import argparse
import re
import tempfile
from pathlib import Path

from make_stage110_synthetic_midframe_rom import make_rom
from run_stage111_native_tile_boundary import run_native
from run_stage112_native_subscanline_sweep import PHASES, validate_sweep
from run_stage113_native_prefetch import verify_report as verify_prefetch
from run_stage114_native_plane_pairs import verify_report as verify_planes

MARKER = "VPD_STAGE115_NATIVE_EDGE_CARRY_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE115_NATIVE_EDGE_CARRY_PASS "
    r"switch_sl=104 observed_lines=16 edge_tiles=32 "
    r"old_tiles=18 new_tiles=14 first_new_sl=105 "
    r"fine_scroll=0 carry_lag_min=(\d+) carry_lag_max=(\d+) "
    r"invalid=0 same_synthetic_frame=yes "
    r"original_game_scroll_proven=no$",
    re.MULTILINE,
)


class CarryError(ValueError):
    pass


def verify_report(log, tile, plane):
    matched = list(PATTERN.finditer(log))
    if len(matched) != 1 or log.count(MARKER) != 1:
        raise CarryError("Missing, malformed or duplicated native cross-line carry proof")
    minimum, maximum = map(int, matched[0].groups())
    if not 1 <= minimum <= maximum <= 1000000:
        raise CarryError("Unsupported or contradictory native source-clock distance")
    if (tile.get("switch_source_scanline") != 104 or
            tile.get("same_buffered_tile_frame_proven") is not True or
            plane.get("source_sl") != 104 or
            plane.get("mixed_pairs_observed") != 0):
        raise CarryError("Unbound same-process native tile/plane evidence")
    return {
        "lookahead_tiles_per_line": 2,
        "lines_checked": 16,
        "old_tiles": 18, "new_tiles": 14,
        "first_new_edge_line": 105,
        "source_carry_min_ticks": minimum,
        "source_carry_max_ticks": maximum,
        "original_game_scroll_proven": False,
    }


def run(binary, private_dir):
    with tempfile.TemporaryDirectory(dir=private_dir) as temp:
        work = Path(temp)
        all_observations = []
        for phase in PHASES:
            path = work / ("phase_%d.nes" % phase)
            make_rom(path, phase_nops=phase)
            tile, log = run_native(
                binary, path, work / ("native_%d" % phase),
                prefetch=True, plane_pairs=True, scanline_carry=True,
            )
            prefetch = verify_prefetch(log, tile)
            plane = verify_planes(log, tile, prefetch)
            carry = verify_report(log, tile, plane)
            all_observations.append((phase, tile, carry))
        fixed = work / "fixed.nes"
        make_rom(fixed, switch=False)
        run_native(binary, fixed, work / "fixed", positive=False,
                   prefetch=True, plane_pairs=True, scanline_carry=True)
        run_native(binary, work / ("phase_%d.nes" % PHASES[-1]),
                   work / "disabled", enabled=False, positive=False,
                   prefetch=True, plane_pairs=True, scanline_carry=True)
    sweep = validate_sweep([
        (phase, tile) for phase, tile, _ in all_observations
    ])
    distances = [carry for _, _, carry in all_observations]
    if any(v["first_new_edge_line"] != 105 or
           v["original_game_scroll_proven"] is not False for v in distances):
        raise CarryError("Contradictory scanline-edge witness across phases")
    print(
        "STAGE115_NATIVE_SCANLINE_CARRY_PROOF native_fceux=yes "
        "synthetic_mapper4_only=yes phases=0,4,8,12 "
        "lines_each=16 carry_tiles_each=32 old_tiles_each=18 new_tiles_each=14 "
        "source_switch_sl=%d first_new_edge_sl=105 fine_scroll=0 "
        "carry_lag_min=%s carry_lag_max=%s "
        "paired_plane_prefetch_tile_xbuf_each=yes "
        "fixed_bank_control=clean disabled_control=clean "
        "original_game_scroll_proven=no" %
        (sweep["switch_sl"],
         ",".join(str(v["source_carry_min_ticks"]) for v in distances),
         ",".join(str(v["source_carry_max_ticks"]) for v in distances))
    )
    return sweep, distances


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("native_fceux", type=Path)
    p.add_argument("private_temp", type=Path)
    args = p.parse_args()
    run(args.native_fceux, args.private_temp)
