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


def categorize_exit(code, output):
    """Public-safe category only. Never expose emulator stderr/ROM paths."""
    if code is None or code == 0 or code == -15:
        return "not_an_early_failure"
    if code == -11 or code == 139:
        return "signal_sigsegv"
    if code == -6 or code == 134:
        return "signal_sigabrt"
    if "Could not load the Qt platform plugin" in output or (
            "no Qt platform plugin could be initialized" in output):
        return "qt_platform_initialization"
    if "Could not initialize SDL" in output:
        return "sdl_initialization"
    return "other_early_process_exit"


def backend_settings(backend, working):
    """Stage101 explicit backend to distinguish offscreen vs virtual X."""
    if backend not in ("dummy", "xvfb"):
        raise ValueError("Unsupported isolated FCEUX display backend")
    if backend == "xvfb" and not os.environ.get("DISPLAY"):
        raise SmokeError("Xvfb backend requested without display server")
    return {
        "QT_QPA_PLATFORM": "offscreen" if backend == "dummy" else "xcb",
        "SDL_VIDEODRIVER": "dummy" if backend == "dummy" else "x11",
        "SDL_AUDIODRIVER": "dummy",
        "QT_OPENGL": "software",
        "LIBGL_ALWAYS_SOFTWARE": "1",
        "XDG_CONFIG_HOME": str(working / "xdg-config"),
        "XDG_CACHE_HOME": str(working / "xdg-cache"),
        "XDG_DATA_HOME": str(working / "xdg-data"),
        "HOME": str(working),
    }


def execute(binary, rom, working, *, newppu, smoke_enabled=True,
            deadline=18.0, backend="dummy"):
    working.mkdir(parents=True, exist_ok=True)
    log_path = working / "execution.log"
    env = os.environ.copy()
    env.update(backend_settings(backend, working))
    env["VPD_STAGE100_SYNTHETIC_SMOKE"] = "1" if smoke_enabled else "0"
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
            stayed_alive = proc.poll() is None
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
        # Survived the observation window; not proof of rendered frames.
        "status": "alive_observation_window" if stayed_alive else "early_exit",
        "exit_category": ("not_an_early_failure" if stayed_alive else
                          categorize_exit(proc.returncode, output)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("private_temp", type=Path)
    parser.add_argument("--backend", choices=("dummy", "xvfb"), default="dummy")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(dir=args.private_temp) as name:
        private = Path(name)
        rom = private / "synthetic.nes"
        make_rom(rom)
        good = execute(args.binary, rom, private / "newppu", newppu=True,
                       backend=args.backend)
        disabled = execute(args.binary, rom, private / "disabled",
                           newppu=True, smoke_enabled=False,
                           backend=args.backend)
        legacy = execute(args.binary, rom, private / "oldppu",
                         newppu=False, smoke_enabled=True,
                         backend=args.backend)
    proof = good["result"]
    legacy_label = ("clean" if legacy["status"] == "alive_observation_window"
                    else "unverified_early_exit")
    disabled_label = ("clean" if disabled["status"] == "alive_observation_window"
                      else "unverified_early_exit")
    print("STAGE100_FCEUX_RUNTIME_TEST_PASS newppu_real_process=yes "
          "synthetic_rom_only=yes observed_raw_steps=8192 raster_proven=no "
          f"disabled_probe_control_status={disabled_label} "
          f"legacy_renderer_status={legacy_label} "
          f"wraps={proof['wraps']} label_changes={proof['label_changes']} "
          f"zero_advance_calls={proof['zero_advance_calls']}")
    print("STAGE101_FCEUX_HEADLESS_CONTROL_REPORT "
          f"backend={args.backend} newppu_runtime_proven=yes "
          f"disabled_probe_status={disabled_label} "
          f"disabled_probe_exit_category={disabled['exit_category']} "
          f"legacy_status={legacy_label} "
          f"legacy_exit_category={legacy['exit_category']} "
          "nes_raster_hardware_timing_proven=no")


if __name__ == "__main__":
    main()
