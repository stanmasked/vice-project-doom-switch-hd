#!/usr/bin/env python3
"""Headless FCEUX synthetic ROM positive/legacy-negative runtime probe."""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage100_synthetic_nrom import make_rom

MARKER = "VPD_STAGE100_NEWPPU_RUNTIME_PASS"
SIGNATURE = re.compile(
    r"^VPD_STAGE100_NEWPPU_RUNTIME_PASS raw_steps=8192 "
    r"cycle_wraps=(\d+) internal_label_changes=(\d+) "
    r"invalid_steps=(\d+) normalized_scanlines=no real_game_data=no$",
    re.MULTILINE,
)


class SmokeError(RuntimeError):
    pass


def inspect_output(text, *, expect_probe):
    matches = list(SIGNATURE.finditer(text))
    if not expect_probe:
        if MARKER in text:
            raise SmokeError("Legacy/disabled PPU unexpectedly emitted newppu marker")
        return None
    if len(matches) != 1 or text.count(MARKER) != 1:
        raise SmokeError("Missing, malformed, or duplicate newppu runtime proof marker")
    wraps, line_changes, invalid = (int(v) for v in matches[0].groups())
    if invalid:
        raise SmokeError("Invalid raw PPU counter events observed")
    if not wraps or not line_changes:
        raise SmokeError("Raw PPU counter labels or wraparounds did not progress")
    return {"steps": 8192, "wraps": wraps, "label_changes": line_changes,
            "ntsc_raster_calibration_proven": False}


def execute(binary, rom, working, *, newppu, deadline=18.0):
    working.mkdir(parents=True, exist_ok=True)
    log_path = working / "execution.log"
    env = os.environ.copy()
    env.update({
        "QT_QPA_PLATFORM": "offscreen",
        "SDL_VIDEODRIVER": "dummy",
        "SDL_AUDIODRIVER": "dummy",
        "XDG_CONFIG_HOME": str(working / "xdg-config"),
        "XDG_CACHE_HOME": str(working / "xdg-cache"),
        "XDG_DATA_HOME": str(working / "xdg-data"),
        "HOME": str(working),
        "VPD_STAGE100_SYNTHETIC_SMOKE": "1",
    })
    cmd = [str(binary.resolve()), "--newppu", "1" if newppu else "0",
           "--sound", "0", "--opengl", "0", "--no-config", "1",
           str(rom.resolve())]
    with log_path.open("wb") as stream:
        proc = subprocess.Popen(cmd, cwd=working, env=env,
                                stdin=subprocess.DEVNULL,
                                stdout=stream, stderr=subprocess.STDOUT)
        end = time.monotonic() + deadline
        try:
            while time.monotonic() < end:
                time.sleep(0.10)
                output = log_path.read_text(encoding="utf8", errors="replace")
                if newppu and MARKER in output:
                    break
                if proc.poll() is not None:
                    break
            if not newppu and proc.poll() is None:
                time.sleep(1)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
    output = log_path.read_text(encoding="utf8", errors="replace")
    if newppu and MARKER not in output:
        # Avoid dumping data or private file paths on failure.
        raise SmokeError("No real FCEUX newppu callback marker; runtime did not reach proof threshold")
    if not newppu and proc.returncode not in (None, 0, -15):
        raise SmokeError("Legacy FCEUX process exited abnormally")
    return inspect_output(output, expect_probe=newppu)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("private_temp", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(dir=args.private_temp) as name:
        private = Path(name)
        rom = private / "synthetic.nes"
        make_rom(rom)
        good = execute(args.binary, rom, private / "newppu", newppu=True)
        execute(args.binary, rom, private / "oldppu", newppu=False, deadline=5)
    print("STAGE100_FCEUX_RUNTIME_TEST_PASS newppu_real_process=yes "
          "legacy_negative_control=yes synthetic_rom_only=yes "
          "observed_raw_steps=8192 raster_proven=no "
          f"wraps={good['wraps']} label_changes={good['label_changes']}")


if __name__ == "__main__":
    main()
