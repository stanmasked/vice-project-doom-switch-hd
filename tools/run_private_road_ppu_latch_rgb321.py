#!/usr/bin/env python3
"""Run real FCEUX and seal one private CPU/RAM/PPU/RGB source capture."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

from audit_private_road_ppu_latch_rgb321 import finalize, preflight, verify
from run_private_fm2_storyboard import private_target


def capture(
    rom: Path,
    movie: Path,
    output_dir: Path,
    fceux: str = "fceux",
    timeout_seconds: int = 1800,
) -> dict:
    if type(timeout_seconds) is not int or not 30 <= timeout_seconds <= 7200:
        raise ValueError("timeout must be between 30 and 7200 seconds")
    if rom.is_symlink() or movie.is_symlink():
        raise ValueError("private ROM/FM2 inputs must not be symbolic links")
    rom = rom.resolve(strict=True)
    movie = movie.resolve(strict=True)

    executable = shutil.which(fceux)
    if executable is None:
        candidate = Path(fceux)
        if candidate.is_file() and os.access(candidate, os.X_OK):
            executable = str(candidate.resolve())
    if executable is None:
        raise ValueError("real FCEUX executable is not available in this workspace")
    script = Path(__file__).with_name("capture_private_road_ppu_latch_rgb321.lua").resolve()
    if not script.is_file():
        raise ValueError("same-session private FCEUX Lua script is missing")
    xvfb = None
    if not os.environ.get("DISPLAY"):
        xvfb = shutil.which("xvfb-run")
        if xvfb is None:
            raise ValueError("headless capture requires xvfb-run or a configured DISPLAY")

    target = private_target(output_dir)
    target.mkdir(mode=0o700)
    identity = preflight(rom, movie, target)
    command = [
        executable, "--no-config", "1", "--sound", "0",
        "--loadlua", str(script), str(rom),
    ]
    if xvfb:
        command = [xvfb, "-a", "-s", "-screen 0 1024x768x24", *command]
    env = os.environ.copy()
    env.update({
        "VPD_PRIVATE_PPU_LATCH_OUTPUT_DIR": str(target),
        "VPD_PRIVATE_FM2_PATH": str(movie),
        "VPD_PRIVATE_ROM_PAYLOAD_MD5": identity["rom_payload_md5"],
        "VPD_PRIVATE_FRAME_COUNT": str(identity["movie_frames"]),
    })
    log_path = target / "fceux_private_session.log"
    process = None
    completed = False
    try:
        with log_path.open("xb") as log:
            process = subprocess.Popen(
                command, cwd=target, env=env, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True,
            )
            deadline = time.monotonic() + timeout_seconds
            while time.monotonic() < deadline:
                if (target / "COMPLETE.txt").is_file():
                    completed = True
                    break
                if process.poll() is not None:
                    raise RuntimeError("FCEUX exited before the same-session capture completed")
                time.sleep(0.25)
            if not completed:
                raise TimeoutError("FCEUX did not complete frames 600–920")
    finally:
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=5)
    if not completed:
        raise RuntimeError("same-session private capture incomplete")
    finalize(rom, movie, target)
    return verify(rom, movie, target)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--movie", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--fceux", default="fceux")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()
    result = capture(
        args.rom, args.movie, args.output_dir,
        fceux=args.fceux, timeout_seconds=args.timeout_seconds,
    )
    print(
        "VPD_PRIVATE_ROAD_PPU_LATCH_RGB321_REAL_FCEUX_PASS"
        f" frames={result['frames']}"
        f" cpu_writes={result['cpu_writer_events']}"
        f" ppu_events={result['ppu_register_events']}"
        f" ram_samples={result['postframe_ram_samples']}"
        f" rgb_slots={result['rgb_slots']}"
        f" cpu_port_values_matched={result['cpu_port_values_matched']}"
        f" cpu_port_cycles_matched={result['cpu_port_cycles_matched']}"
        " same_session=yes raw_source_values_disclosed=no"
        " effective_ppu_scroll_proven=no"
    )


if __name__ == "__main__":
    main()
