#!/usr/bin/env python3
"""Stage102: private Xvfb runtime proof of FCEUX PPU_status writes, not NES VBlank.

Only print aggregate intervals from synthetic NROM; never dump PPU positions.
"""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage100_synthetic_nrom import make_rom
from run_stage100_fceux_synthetic_smoke import backend_settings, categorize_exit

MARKER = "VPD_STAGE102_NATIVE_STATUS_WINDOW_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE102_NATIVE_STATUS_WINDOW_PASS entries=3 clears=3 "
    r"entry_period_min=(\d+) entry_period_max=(\d+) "
    r"entry_to_clear_min=(\d+) entry_to_clear_max=(\d+) "
    r"invalid=(\d+) hardware_vblank_proven=no raw_positions=no$",
    re.MULTILINE,
)


class WindowError(ValueError):
    pass


def verify_window(text):
    hits = list(PATTERN.finditer(text))
    if len(hits) != 1 or text.count(MARKER) != 1:
        raise WindowError("Missing, malformed or duplicate native status window marker")
    period_min, period_max, window_min, window_max, invalid = (
        int(v) for v in hits[0].groups())
    if invalid:
        raise WindowError("Invalid native status-write pairing detected")
    if not (0 < period_min <= period_max <= 1000000):
        raise WindowError("Native entry interval is missing or unreasonable")
    if not (0 < window_min <= window_max < period_min):
        raise WindowError("Native status-clear window exceeds entry period")
    return {
        "source_status_entries": 3,
        "source_status_clears": 3,
        "min_entry_interval_internal_ticks": period_min,
        "max_entry_interval_internal_ticks": period_max,
        "min_entry_to_clear_internal_ticks": window_min,
        "max_entry_to_clear_internal_ticks": window_max,
        "nes_physical_vblank_proven": False,
        "original_game_pixels_observed": False,
    }


def run(binary, private, *, timeout=20):
    private = Path(private)
    with tempfile.TemporaryDirectory(dir=private) as name:
        working = Path(name)
        rom = working / "original_synthetic.nes"
        make_rom(rom)
        env = os.environ.copy()
        env.update(backend_settings("xvfb", working))
        env["VPD_STAGE100_SYNTHETIC_SMOKE"] = "0"
        env["VPD_STAGE102_STATUS_PROBE"] = "1"
        cmd = [str(Path(binary).resolve()), "--newppu", "1",
               "--sound", "0", "--opengl", "0", "--no-config", "1",
               str(rom)]
        log = working / "runtime.log"
        with log.open("wb") as stream:
            proc = subprocess.Popen(cmd, env=env, cwd=working,
                                    stdin=subprocess.DEVNULL,
                                    stdout=stream, stderr=subprocess.STDOUT)
            end = time.monotonic() + timeout
            try:
                while time.monotonic() < end:
                    time.sleep(0.1)
                    if MARKER in log.read_text(encoding="utf8", errors="replace"):
                        break
                    if proc.poll() is not None:
                        break
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=4)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=4)
        content = log.read_text(encoding="utf8", errors="replace")
        if MARKER not in content:
            raise WindowError(
                "No synthetic FCEUX source-status window; exit_category=" +
                categorize_exit(proc.returncode, content))
        evidence = verify_window(content)
    print("STAGE102_FCEUX_NATIVE_STATUS_PROOF "
          "synthetic_rom_only=yes source_status_assignments_observed=yes "
          "entries=3 clears=3 "
          f"entry_interval_min={evidence['min_entry_interval_internal_ticks']} "
          f"entry_interval_max={evidence['max_entry_interval_internal_ticks']} "
          f"entry_to_clear_min={evidence['min_entry_to_clear_internal_ticks']} "
          f"entry_to_clear_max={evidence['max_entry_to_clear_internal_ticks']} "
          "hardware_vblank_proven=no original_level_geometry_proven=no")
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fceux", type=Path)
    parser.add_argument("private_runner_directory", type=Path)
    args = parser.parse_args()
    run(args.fceux, args.private_runner_directory)


if __name__ == "__main__":
    main()
