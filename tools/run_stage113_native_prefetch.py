#!/usr/bin/env python3
"""Source-tick prefetch/read-to-render timing across four synthetic MMC3 phases."""
import argparse
import re
import tempfile
from pathlib import Path

from make_stage110_synthetic_midframe_rom import make_rom
from run_stage111_native_tile_boundary import run_native
from run_stage112_native_subscanline_sweep import PHASES, validate_sweep

MARKER = "VPD_STAGE113_NATIVE_PREFETCH_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE113_NATIVE_PREFETCH_PASS "
    r"switch_sl=(\d+) first_new_sl=(\d+) first_new_xt=(\d+) "
    r"lookahead_tiles=2 matched_old=128 matched_new=128 "
    r"old_after_write=(\d+) old_prefetched_before=(\d+) "
    r"old_read_started_after=(\d+) new_read_started_after=128 "
    r"fetch_to_draw_min=(\d+) fetch_to_draw_max=(\d+) invalid=0 "
    r"paired_tile_xbuf_frame=yes synthetic_only=yes "
    r"original_game_prefetch_proven=no$", re.MULTILINE,
)


class PrefetchError(ValueError):
    pass


def verify_report(log, stage111):
    matches = list(PATTERN.finditer(log))
    if len(matches) != 1 or log.count(MARKER) != 1:
        raise PrefetchError("Missing, malformed or repeated native prefetch proof")
    (sl, new_sl, new_xt, old, before, after, lo, hi) = map(
        int, matches[0].groups())
    if (not 40 <= sl <= 210 or
            sl != stage111.get("switch_source_scanline") or
            new_sl != stage111.get("first_new_source_scanline") or
            new_xt != stage111.get("first_new_xt") or
            old != stage111.get("transient_old_tiles") or
            old > 64 or old != before + after or
            not 0 < lo <= hi <= 1000000 or
            stage111.get("same_buffered_tile_frame_proven") is not True):
        raise PrefetchError("Unbound source record origin or impossible fetch lag")
    return {
        "switch_source_scanline": sl,
        "first_new_source_scanline": new_sl,
        "first_new_xt": new_xt,
        "transient_old_tiles": old,
        "old_reads_started_before_switch": before,
        "old_reads_started_after_switch": after,
        "fetch_to_draw_min_source_ticks": lo,
        "fetch_to_draw_max_source_ticks": hi,
        "same_buffered_tile_frame_proven": True,
        "original_game_tile_proven": False,
        "original_game_prefetch_proven": False,
    }


def validate_prefetch_sweep(records):
    # First validate actual buffered first-new tile positions for all phases.
    source = [(phase, tile) for phase, tile, _ in records]
    phase_sweep = validate_sweep(source)
    if len(records) != len(PHASES):
        raise PrefetchError("Missing one or more paired native prefetch samples")
    matched = []
    for phase, tile, provenance in records:
        if (phase not in PHASES or
                provenance["first_new_xt"] != tile["first_new_xt"] or
                provenance["first_new_source_scanline"] !=
                tile["first_new_source_scanline"] or
                provenance["transient_old_tiles"] != tile["transient_old_tiles"] or
                provenance["original_game_prefetch_proven"] is not False):
            raise PrefetchError("Timeline mismatch between fetch buffer and XBuf")
        matched.append(provenance)
    return phase_sweep, matched


def run(binary, temp):
    with tempfile.TemporaryDirectory(dir=temp) as location:
        root = Path(location)
        records = []
        for phase in PHASES:
            rom = root / ("phase_%d.nes" % phase)
            make_rom(rom, phase_nops=phase)
            tile, log = run_native(binary, rom, root / ("observed_%d" % phase),
                                   prefetch=True)
            original = verify_report(log, tile)
            records.append((phase, tile, original))
        fixed = root / "fixed.nes"
        make_rom(fixed, switch=False)
        run_native(binary, fixed, root / "fixed", positive=False, prefetch=True)
        run_native(binary, root / ("phase_%d.nes" % PHASES[-1]),
                   root / "disabled", enabled=False,
                   positive=False, prefetch=True)
        sweep, observations = validate_prefetch_sweep(records)
    print(
        "STAGE113_NATIVE_BG_PREFETCH_PROOF native_fceux=yes "
        "synthetic_mapper4_only=yes phases=0,4,8,12 "
        "lookahead_tiles=2 matched_old_each=128 matched_new_each=128 "
        "source_sl=%d first_new_xt=%s old_after_write=%s "
        "old_fetch_started_before=%s old_fetch_started_after=%s "
        "source_fetch_to_draw_min=%s source_fetch_to_draw_max=%s "
        "paired_tile_and_framebuffer_each=yes "
        "fixed_bank_control=clean disabled_control=clean "
        "physical_nes_dot_timing_proven=no original_game_prefetch_proven=no" %
        (sweep["switch_sl"],
         ",".join(str(s["first_new_xt"]) for s in observations),
         ",".join(str(s["transient_old_tiles"]) for s in observations),
         ",".join(str(s["old_reads_started_before_switch"]) for s in observations),
         ",".join(str(s["old_reads_started_after_switch"]) for s in observations),
         ",".join(str(s["fetch_to_draw_min_source_ticks"]) for s in observations),
         ",".join(str(s["fetch_to_draw_max_source_ticks"]) for s in observations))
    )
    return sweep, observations


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_fceux", type=Path)
    parser.add_argument("private_temp", type=Path)
    args = parser.parse_args()
    run(args.native_fceux, args.private_temp)
