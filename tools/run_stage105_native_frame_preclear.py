#!/usr/bin/env python3
"""Stage105 pinned native FCEUX PPUSTATUS pre-clear vs CPU $2002 read audit.

Synthetic NROM and Xvfb only. All evidence is source-level emulator behavior.
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

MARKER = "VPD_STAGE105_NATIVE_PRECLEAR_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE105_NATIVE_PRECLEAR_PASS reads=16384 "
    r"sets=(\d+) clears=(\d+) pre_calls=(\d+) high_reads=(\d+) "
    r"read_clears=(\d+) low_after_high=(\d+) "
    r"pre_low_after_high=(\d+) pre_high_after_high=(\d+) "
    r"pre_high_no_read=(\d+) pre_low_no_read=(\d+) "
    r"high_to_pre_min=(\d+) high_to_pre_max=(\d+) invalid=(\d+) "
    r"source_only=yes hardware_vblank_proven=no$",
    re.MULTILINE,
)


class PreclearError(ValueError):
    pass


def verify_preclear(text):
    found = list(PATTERN.finditer(text))
    if len(found) != 1 or text.count(MARKER) != 1:
        raise PreclearError("Missing, malformed or duplicate FCEUX pre-clear proof")
    (sets, clears, pre_calls, high, read_clears, low_after,
     pre_low_after, pre_high_after, pre_high_unread, pre_low_unread,
     lag_min, lag_max, invalid) = (int(v) for v in found[0].groups())
    if invalid or pre_high_after:
        raise PreclearError("Status bit returned or persisted incorrectly")
    if not (2 <= sets <= 16384 and 1 <= clears <= sets and
            sets - clears <= 1 and pre_calls == clears):
        raise PreclearError("Unpaired native status frame pre/post clear callbacks")
    if not (0 < high == read_clears <= sets and
            0 < pre_low_after <= min(high, clears)):
        raise PreclearError("Missing CPU read-clear preceding native frame clear")
    if pre_low_after + pre_high_unread + pre_low_unread != pre_calls:
        raise PreclearError("Native pre-clear categories do not cover all frame clears")
    if low_after == 0:
        raise PreclearError("No low CPU reads observed following high-bit clear")
    if not (0 <= lag_min <= lag_max <= 1000000):
        raise PreclearError("Invalid read-to-frame-clear internal tick offset")
    return {
        "cpu_reads": 16384, "source_sets": sets, "source_clears": clears,
        "preclear_observations": pre_calls, "cpu_high_reads": high,
        "cpu_high_bit_clears": read_clears,
        "low_reads_after_high": low_after,
        "frame_clears_preceded_by_cpu_read": pre_low_after,
        "preclear_bit_high_without_cpu_high_read": pre_high_unread,
        "preclear_bit_low_without_cpu_high_read": pre_low_unread,
        "read_to_frame_clear_lag_min": lag_min,
        "read_to_frame_clear_lag_max": lag_max,
        "hardware_vblank_proven": False,
        "original_first_level_proven": False,
    }


def execute(binary, rom, folder, *, enabled, timeout=20.0):
    folder.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(backend_settings("xvfb", folder))
    for tag in (
        "VPD_STAGE100_SYNTHETIC_SMOKE", "VPD_STAGE102_STATUS_PROBE",
        "VPD_STAGE103_PPUSTATUS_READ_PROBE", "VPD_STAGE104_EVENT_ORDER_PROBE",
    ):
        env[tag] = "0"
    env["VPD_STAGE105_PRECLEAR_PROBE"] = "1" if enabled else "0"
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
            raise PreclearError("Disabled pre-clear observer unexpectedly emitted marker")
        if not survived:
            raise PreclearError("Disabled pre-clear run exited early: " +
                                categorize_exit(proc.returncode, content))
        return None
    if MARKER not in content:
        raise PreclearError("No native pre-clear witness; exit_category=" +
                            categorize_exit(proc.returncode, content))
    return verify_preclear(content)


def run(binary, private):
    with tempfile.TemporaryDirectory(dir=private) as name:
        folder = Path(name)
        rom = folder / "synthetic_ppustatus_poll.nes"
        make_ppustatus_poll_rom(rom)
        proof = execute(binary, rom, folder / "enabled", enabled=True)
        execute(binary, rom, folder / "disabled", enabled=False)
    print(
        "STAGE105_FCEUX_NATIVE_PRECLEAR_PROOF "
        "synthetic_rom_only=yes disabled_observer_control=clean "
        "reads=16384 "
        f"frame_clears={proof['source_clears']} "
        f"preclear_already_low_after_cpu_read={proof['frame_clears_preceded_by_cpu_read']} "
        f"preclear_high_without_cpu_read={proof['preclear_bit_high_without_cpu_high_read']} "
        f"read_to_frame_clear_min={proof['read_to_frame_clear_lag_min']} "
        f"read_to_frame_clear_max={proof['read_to_frame_clear_lag_max']} "
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
