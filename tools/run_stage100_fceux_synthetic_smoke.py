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
    r"invalid_steps=(\d+) zero_advance_calls=(\d+) "
    r"normalized_scanlines=no real_game_data=no$",
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
    wraps, line_changes, invalid, zero_calls = (int(v) for v in matches[0].groups())
    if invalid:
        raise SmokeError("Invalid raw PPU counter events observed: " + str(invalid))
    if not wraps or not line_changes:
        raise SmokeError("Raw PPU counter labels or wraparounds did not progress")
    return {"steps": 8192, "wraps": wraps, "label_changes": line_changes,
            "zero_advance_calls": zero_calls,
            "ntsc_raster_calibration_proven": False}


def execute(binary, rom, working, *, newppu, smoke_enabled=True, deadline=18.0):
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
        "VPD_STAGE100_SYNTHETIC_SMOKE": "1" if smoke_enabled else "0",
    })
    cmd = [str(binary.resolve()), "--newppu", "1" if newppu else "0",
           "--sound", "0", "--opengl", "0", "--no-config", "1",
           str(rom.resolve())]
    expect_marker = newppu and smoke_enabled
    with log_path.open("wb") as stream:
        proc = subprocess.Popen(cmd, cwd=working, env=env,
                                stdin=subprocess.DEVNULL,
                                stdout=stream, stderr=subprocess.STDOUT)
        end = time.monotonic() + (deadline if expect_marker else 2.0)
        try:
            while time.monotonic() < end:
                time.sleep(0.10)
                output = log_path.read_text(encoding="utf8", errors="replace")
                if expect_marker and MARKER in output:
                    break
                if proc.poll() is not None:
                    break
            # Negative controls have a bounded execution window, not a marker.
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
    output = log_path.read_text(encoding="utf8", errors="replace")
    if expect_marker and MARKER not in output:
        # Avoid dumping data or private file paths on failure.
        raise SmokeError("No real FCEUX newppu callback marker; runtime did not reach proof threshold")
    result = inspect_output(output, expect_probe=expect_marker)
    if expect_marker:
        return {"status": "verified", "result": result}
    return {
        "status": ("completed_or_terminated"
                   if proc.returncode in (0, -15)
                   else "early_exit"),
        "exit_code": proc.returncode,
    }


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
        disabled = execute(args.binary, rom, private / "disabled",
                           newppu=True, smoke_enabled=False)
        if disabled["status"] != "completed_or_terminated":
            raise SmokeError("Runtime without synthetic smoke opt-in is not stable")
        legacy = execute(args.binary, rom, private / "oldppu",
                         newppu=False, smoke_enabled=True)
    proof = good["result"]
    legacy_label = ("clean" if legacy["status"] == "completed_or_terminated"
                    else "unverified_early_exit")
    print("STAGE100_FCEUX_RUNTIME_TEST_PASS newppu_real_process=yes "
          "smoke_disabled_negative_control=yes synthetic_rom_only=yes "
          "observed_raw_steps=8192 raster_proven=no "
          f"legacy_renderer_status={legacy_label} "
          f"wraps={proof['wraps']} label_changes={proof['label_changes']} "
          f"zero_advance_calls={proof['zero_advance_calls']}")


if __name__ == "__main__":
    main()
