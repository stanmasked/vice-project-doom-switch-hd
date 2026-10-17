#!/usr/bin/env python3
"""Stage103: actual pinned FCEUX $2002 read/clear positive and negative tests.

Xvfb mode, private synthetic NROM, aggregate counters only; NOT NES hardware.
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

MARKER = "VPD_STAGE103_NATIVE_PPUSTATUS_READ_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE103_NATIVE_PPUSTATUS_READ_PASS reads=16384 "
    r"returned_high=(\d+) before_high=(\d+) cleared_high=(\d+) "
    r"after_high=(\d+) invalid=(\d+) source_only=yes "
    r"hardware_vblank_proven=no$",
    re.MULTILINE,
)


class ReadProbeError(ValueError):
    pass


def verify_read_marker(text):
    matches = list(PATTERN.finditer(text))
    if len(matches) != 1 or text.count(MARKER) != 1:
        raise ReadProbeError("Missing/duplicate/malformed native $2002 marker")
    returned, before, cleared, after, invalid = (
        int(x) for x in matches[0].groups())
    if not 0 < before <= 16384:
        raise ReadProbeError("No real high VBlank status encountered by CPU reads")
    if returned != before or cleared != before:
        raise ReadProbeError("Register return and native high-bit clear disagree")
    if after or invalid:
        raise ReadProbeError("Native register read did not clear high bit")
    return {
        "synthetic_cpu_reads": 16384,
        "source_high_returned": returned,
        "source_high_before": before,
        "source_high_cleared": cleared,
        "source_high_after": after,
        "native_read_path_exercised": True,
        "physical_nes_vblank_proven": False,
        "original_game_raster_proven": False,
    }


def execute(binary, rom, folder, *, enabled, deadline=20.0):
    folder.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(backend_settings("xvfb", folder))
    env["VPD_STAGE100_SYNTHETIC_SMOKE"] = "0"
    env["VPD_STAGE102_STATUS_PROBE"] = "0"
    env["VPD_STAGE103_PPUSTATUS_READ_PROBE"] = "1" if enabled else "0"
    cmd = [str(Path(binary).resolve()), "--newppu", "1",
           "--sound", "0", "--opengl", "0", "--no-config", "1",
           str(rom.resolve())]
    path = folder / "execution.log"
    with path.open("wb") as stream:
        process = subprocess.Popen(cmd, cwd=folder, env=env,
                                   stdin=subprocess.DEVNULL,
                                   stdout=stream, stderr=subprocess.STDOUT)
        end = time.monotonic() + (deadline if enabled else 2)
        try:
            while time.monotonic() < end:
                time.sleep(0.1)
                if enabled and MARKER in path.read_text(encoding="utf8",
                                                         errors="replace"):
                    break
                if process.poll() is not None:
                    break
            survived = process.poll() is None
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    output = path.read_text(encoding="utf8", errors="replace")
    if not enabled:
        if MARKER in output:
            raise ReadProbeError("Disabled native $2002 observer emitted marker")
        if not survived:
            raise ReadProbeError("Disabled-observer control exited early: " +
                                 categorize_exit(process.returncode, output))
        return None
    if MARKER not in output:
        raise ReadProbeError("No real FCEUX $2002 read probe after synthetic CPU polling; exit_category=" +
                             categorize_exit(process.returncode, output))
    return verify_read_marker(output)


def run(binary, private):
    with tempfile.TemporaryDirectory(dir=private) as directory:
        folder = Path(directory)
        rom = folder / "synthetic_ppustatus_poll.nes"
        make_ppustatus_poll_rom(rom)
        proof = execute(binary, rom, folder / "enabled", enabled=True)
        execute(binary, rom, folder / "disabled", enabled=False)
    print("STAGE103_FCEUX_NATIVE_PPUSTATUS_READ_PROOF "
          "synthetic_rom_only=yes positive_cpu_poll=yes "
          "disabled_probe_control=clean reads=16384 "
          f"returned_high={proof['source_high_returned']} "
          f"cleared_high={proof['source_high_cleared']} "
          "invalid=0 physical_vblank_proven=no hd_geometry_ready=no")
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fceux", type=Path)
    parser.add_argument("private_runner_temp", type=Path)
    args = parser.parse_args()
    run(args.fceux, args.private_runner_temp)


if __name__ == "__main__":
    main()
