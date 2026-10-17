#!/usr/bin/env python3
"""Native stage112 controlled NOP-phase sweep of the MMC3 midframe tile boundary.

A phase inserts original 6502 NOP opcodes before the second $8001 write.
Each FCEUX process must independently prove buffered BG tiles and final XBuf.
No original game raster or hardware timing is inferred.
"""
import argparse
import tempfile
from pathlib import Path

from make_stage110_synthetic_midframe_rom import make_rom
from run_stage111_native_tile_boundary import run_native

PHASES = (0, 4, 8, 12)


class SweepError(ValueError):
    pass


def validate_sweep(phase_records):
    if len(phase_records) != len(PHASES):
        raise SweepError("Insufficient native phase observations")
    if any(not isinstance(phase, int) or phase != required
           for (phase, _), required in zip(phase_records, PHASES)):
        raise SweepError("Duplicated, missing or misordered synthetic phase")
    reports = [report for _, report in phase_records]
    if any(report.get("same_buffered_tile_frame_proven") is not True or
           report.get("original_game_tile_proven") is not False
           for report in reports):
        raise SweepError("Missing buffered BG tile evidence or forged real-game claim")
    source_lines = [report["switch_source_scanline"] for report in reports]
    first_lines = [report["first_new_source_scanline"] for report in reports]
    first_columns = [report["first_new_xt"] for report in reports]
    last_columns = [report["last_rendered_xt"] for report in reports]
    if not (all(40 <= s <= 210 for s in source_lines) and
            all(0 <= c < 32 for c in first_columns + last_columns) and
            all(s == source_lines[0] for s in source_lines)):
        raise SweepError("NOP sweep crossed source scanline or had invalid columns")
    # One tile = 8 pixels. Compare linear row*32+column to avoid mistaken
    # line-wrap ordering, even though the write itself must stay on one line.
    positions = [sl * 32 + xt for sl, xt in zip(first_lines, first_columns)]
    switch_positions = [sl * 32 + xt for sl, xt in zip(source_lines, last_columns)]
    if any(b <= a for a, b in zip(positions, positions[1:])):
        raise SweepError("Increasing CPU NOP phase did not shift the first new tile")
    if any(b <= a for a, b in zip(switch_positions, switch_positions[1:])):
        raise SweepError("Observed MMC3 write boundary did not move monotonically")
    if any(first < last or first > last + 6 for first, last in
           zip(positions, switch_positions)):
        raise SweepError("Prefetched tile bound inconsistent with observed write")
    return {
        "phase_nops": list(PHASES),
        "switch_sl": source_lines[0],
        "switch_columns": last_columns,
        "first_new_columns": first_columns,
        "first_new_lines": first_lines,
        "relative_first_new_tiles": [v - positions[0] for v in positions],
        "original_game_raster_proven": False,
    }


def run(binary, private_temp):
    with tempfile.TemporaryDirectory(dir=private_temp) as private:
        root = Path(private)
        observations = []
        for phase in PHASES:
            rom = root / ("phase_%d.nes" % phase)
            make_rom(rom, phase_nops=phase)
            report = run_native(binary, rom, root / ("observed_%d" % phase))
            observations.append((phase, report))
        fixed = root / "fixed.nes"
        make_rom(fixed, switch=False, phase_nops=PHASES[0])
        run_native(binary, fixed, root / "fixed_control", positive=False)
        run_native(binary, root / ("phase_%d.nes" % PHASES[-1]),
                   root / "disabled_control", enabled=False, positive=False)
        verdict = validate_sweep(observations)
    print(
        "STAGE112_NATIVE_SUBSCANLINE_TILE_SWEEP_PASS "
        "native_fceux=yes synthetic_mapper4_only=yes phases=0,4,8,12 "
        "source_switch_sl=%d "
        "switch_xt=%s first_new_xt=%s first_new_sl=%s "
        "same_line_switch=yes monotone_tile_boundary=yes "
        "paired_buffered_tile_and_xbuf=yes "
        "fixed_bank_control=clean disabled_control=clean "
        "original_game_raster_proven=no" %
        (verdict["switch_sl"],
         ",".join(str(c) for c in verdict["switch_columns"]),
         ",".join(str(c) for c in verdict["first_new_columns"]),
         ",".join(str(c) for c in verdict["first_new_lines"]))
    )
    return verdict


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("native_fceux", type=Path)
    p.add_argument("private_temp", type=Path)
    args = p.parse_args()
    run(args.native_fceux, args.private_temp)
