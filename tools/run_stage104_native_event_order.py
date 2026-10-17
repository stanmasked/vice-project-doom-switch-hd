#!/usr/bin/env python3
"""Stage104 synthetic native FCEUX timeline of frame writes vs CPU $2002 reads.

Aggregate verification only: internal emulation ticks ≠ physical NES raster.
"""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage103_ppustatus_poll_rom import make_ppustatus_poll_rom
from run_stage100_fceux_synthetic_smoke import backend_settings, categorize_exit

MARKER = "VPD_STAGE104_NATIVE_EVENT_ORDER_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE104_NATIVE_EVENT_ORDER_PASS reads=16384 "
    r"source_entries=(\d+) source_clears=(\d+) "
    r"high_reads=(\d+) high_read_clears=(\d+) "
    r"high_within_window=(\d+) low_after_high=(\d+) "
    r"high_lag_min=(\d+) high_lag_max=(\d+) invalid=(\d+) "
    r"source_timeline_only=yes physical_vblank_proven=no$",
    re.MULTILINE,
)


class EventOrderError(ValueError):
    pass


def verify_timeline(text):
    found = list(PATTERN.finditer(text))
    if len(found) != 1 or text.count(MARKER) != 1:
        raise EventOrderError("Missing, malformed or duplicate native timeline marker")
    (entries, clears, high, high_clears, high_within,
     low_after_high, lag_min, lag_max, invalid) = (
        int(v) for v in found[0].groups())
    if invalid:
        raise EventOrderError("Native event ordering inconsistency")
    if not (2 <= entries <= 16384 and 1 <= clears <= entries and
            entries - clears <= 1):
        raise EventOrderError("Missing or nonconsecutive source VBlank windows")
    if not (0 < high == high_clears == high_within <= entries):
        raise EventOrderError("CPU high-bit reads were not paired with source windows")
    if low_after_high == 0:
        raise EventOrderError("No follow-up low reads after CPU read-clear")
    if not (0 <= lag_min <= lag_max <= 1000000):
        raise EventOrderError("Invalid internal tick offset range")
    return {
        "native_cpu_reads": 16384,
        "source_status_entries": entries,
        "source_status_clears": clears,
        "high_cpu_reads": high,
        "high_cpu_read_clears": high_clears,
        "high_cpu_reads_during_source_window": high_within,
        "low_cpu_reads_after_high": low_after_high,
        "high_read_lag_min_internal_ticks": lag_min,
        "high_read_lag_max_internal_ticks": lag_max,
        "source_event_order_verified": True,
        "hardware_ppu_vblank_proven": False,
        "original_level_geometry_proven": False,
    }


def execute(binary, rom, folder, *, enabled, timeout=20.0):
    folder.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(backend_settings("xvfb", folder))
    env["VPD_STAGE100_SYNTHETIC_SMOKE"] = "0"
    env["VPD_STAGE102_STATUS_PROBE"] = "0"
    env["VPD_STAGE103_PPUSTATUS_READ_PROBE"] = "0"
    env["VPD_STAGE104_EVENT_ORDER_PROBE"] = "1" if enabled else "0"
    cmd = [str(Path(binary).resolve()), "--newppu", "1",
           "--sound", "0", "--opengl", "0", "--no-config", "1",
           str(rom.resolve())]
    log = folder / "execution.log"
    with log.open("wb") as stream:
        proc = subprocess.Popen(cmd, env=env, cwd=folder,
                                stdin=subprocess.DEVNULL,
                                stdout=stream, stderr=subprocess.STDOUT)
        end = time.monotonic() + (timeout if enabled else 2.0)
        try:
            while time.monotonic() < end:
                time.sleep(0.1)
                content = log.read_text(encoding="utf8", errors="replace")
                if enabled and MARKER in content:
                    break
                if proc.poll() is not None:
                    break
            survived = proc.poll() is None
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=4)
    content = log.read_text(encoding="utf8", errors="replace")
    if not enabled:
        if MARKER in content:
            raise EventOrderError("Disabled native timeline unexpectedly emitted evidence")
        if not survived:
            raise EventOrderError("Disabled timeline control exited early: " +
                                  categorize_exit(proc.returncode, content))
        return None
    if MARKER not in content:
        raise EventOrderError("No native FCEUX timeline witness; exit_category=" +
                              categorize_exit(proc.returncode, content))
    return verify_timeline(content)


def run(binary, private):
    with tempfile.TemporaryDirectory(dir=private) as temp:
        folder = Path(temp)
        rom = folder / "synthetic_2002_poll.nes"
        make_ppustatus_poll_rom(rom)
        proof = execute(binary, rom, folder / "enabled", enabled=True)
        execute(binary, rom, folder / "disabled", enabled=False)
    print(
        "STAGE104_FCEUX_NATIVE_EVENT_ORDER_PROOF "
        "synthetic_rom_only=yes disabled_probe_control=clean "
        "reads=16384 "
        f"entries={proof['source_status_entries']} "
        f"frame_clears={proof['source_status_clears']} "
        f"high_reads={proof['high_cpu_reads']} "
        f"low_after_high={proof['low_cpu_reads_after_high']} "
        f"high_lag_min={proof['high_read_lag_min_internal_ticks']} "
        f"high_lag_max={proof['high_read_lag_max_internal_ticks']} "
        "hardware_vblank_proven=no original_level_geometry_proven=no"
    )
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("private_runner_dir", type=Path)
    args = parser.parse_args()
    run(args.binary, args.private_runner_dir)


if __name__ == "__main__":
    main()
