#!/usr/bin/env python3
"""Verify time-ordered MMC3 bank write, CHR fetch and rendered BG pixels in FCEUX.

Independent controlled synthetic ROMs only; all events use the same source
runppu-tick counter. A timestamp equality is allowed (PPU-clock granularity).
"""
import argparse
import re
import tempfile
from pathlib import Path

from make_stage107_synthetic_chr_pixel_rom import make_rom
from run_stage108_native_bg_fetch import execute, verify_pair as verify_fetch_pixel_pair

MARKER = "VPD_STAGE109_NATIVE_CHR_TIMELINE_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE109_NATIVE_CHR_TIMELINE_PASS writes=1 fetches=8192 "
    r"pixels=32768 bank=(\d+) first_fetch_lag=(\d+) "
    r"first_pixel_after_fetch_lag=(\d+) last_pixel_after_write_lag=(\d+) "
    r"invalid=(\d+) synthetic_only=yes original_game_timing_proven=no$",
    re.MULTILINE,
)


class TimelineError(ValueError):
    pass


def verify_timeline(output, *, bank):
    matches = list(PATTERN.finditer(output))
    if len(matches) != 1 or output.count(MARKER) != 1:
        raise TimelineError("Missing, duplicate or malformed native write/read/pixel proof")
    observed, first_fetch, first_pixel, last_pixel, invalid = map(int, matches[0].groups())
    if observed != bank or invalid:
        raise TimelineError("Bank mismatch or invalid native chronology")
    if not (0 <= first_fetch <= last_pixel <= 1000000 and
            0 <= first_pixel <= last_pixel and
            first_fetch + first_pixel <= last_pixel):
        raise TimelineError("Contradictory source-clock ordering or overflow")
    return {"bank": observed, "first_fetch_after_write_ticks": first_fetch,
            "first_pixel_after_first_fetch_ticks": first_pixel,
            "last_pixel_after_write_ticks": last_pixel,
            "source_clock_order_verified": True, "physical_raster_verified": False}


def run(binary, private_folder):
    with tempfile.TemporaryDirectory(dir=private_folder) as temporary:
        work = Path(temporary)
        rom0, rom1 = work / "blank.nes", work / "filled.nes"
        make_rom(rom0, 0)
        make_rom(rom1, 1)
        fetch0, pixel0, output0 = execute(binary, rom0, work / "bank0", timeline=True)
        fetch1, pixel1, output1 = execute(binary, rom1, work / "bank1", timeline=True)
        time0 = verify_timeline(output0, bank=0)
        time1 = verify_timeline(output1, bank=1)
        verify_fetch_pixel_pair(fetch0, fetch1, pixel0, pixel1)
        execute(binary, rom1, work / "disabled", enabled=False, timeline=True)
    print(
        "STAGE109_NATIVE_CHR_TIMELINE_PASS synthetic_mapper4_only=yes "
        "native_fceux=yes banks=2 writes_each=1 fetches_each=8192 pixels_each=32768 "
        "source_clock_order_verified=yes paired_native_framebuffer=yes "
        "disabled_control=clean original_game_raster_proven=no "
        "first_fetch_lag_bank0=%d first_fetch_lag_bank1=%d" %
        (time0["first_fetch_after_write_ticks"], time1["first_fetch_after_write_ticks"])
    )
    return (time0, time1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_fceux", type=Path)
    parser.add_argument("private_temp", type=Path)
    args = parser.parse_args()
    run(args.native_fceux, args.private_temp)
