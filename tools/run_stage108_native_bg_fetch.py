#!/usr/bin/env python3
"""Verify FCEUX CHR reads and framebuffer changes in two controlled ROM runs.

This pairs native Stage108 pattern-fetch proof with Stage107 framebuffer
proof from *the same processes*; no original Vice ROM is read or published.
"""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage107_synthetic_chr_pixel_rom import make_rom
from run_stage107_native_bg_pixels import (
    MARKER as PIXEL_MARKER, verify_report as verify_pixels,
    verify_pair as verify_pixel_pair,
)
from run_stage100_fceux_synthetic_smoke import backend_settings, categorize_exit

MARKER = "VPD_STAGE108_NATIVE_BG_FETCH_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE108_NATIVE_BG_FETCH_PASS reads=8192 "
    r"low=4096 high=4096 zero=(\d+) ff=(\d+) other=(\d+) "
    r"paired=4096 invalid=(\d+) synthetic_only=yes "
    r"original_game_fetch_proven=no$", re.MULTILINE
)


class FetchProofError(ValueError):
    pass


def verify_fetch(output):
    items = list(PATTERN.finditer(output))
    if len(items) != 1 or output.count(MARKER) != 1:
        raise FetchProofError("Missing, malformed or duplicate native background fetch proof")
    zero, ff, other, invalid = map(int, items[0].groups())
    if invalid or other or zero + ff != 8192:
        raise FetchProofError("Wrong data, CHR read count, or broken plane-pair sequence")
    return {"reads": 8192, "zero": zero, "ff": ff,
            "original_game_fetch_proven": False}


def verify_pair(empty_fetch, full_fetch, empty_pixel, full_pixel):
    if empty_fetch["zero"] < 8000 or empty_fetch["ff"] > 192:
        raise FetchProofError("Blank selected CHR bank not seen by PPU read path")
    if full_fetch["ff"] < 8000 or full_fetch["zero"] > 192:
        raise FetchProofError("Filled selected CHR bank not seen by PPU read path")
    try:
        verify_pixel_pair(empty_pixel, full_pixel)
    except ValueError as exc:
        raise FetchProofError("Fetch difference not paired with framebuffer difference") from exc
    return {"synthetic_chr_fetch_and_pixels_proven": True,
            "original_game_fetch_proven": False}


def execute(binary, rom, folder, enabled=True, timeout=25.0):
    folder.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(backend_settings("xvfb", folder))
    for var in ("VPD_STAGE100_SYNTHETIC_SMOKE", "VPD_STAGE102_STATUS_PROBE",
                "VPD_STAGE103_PPUSTATUS_READ_PROBE", "VPD_STAGE104_EVENT_ORDER_PROBE",
                "VPD_STAGE105_PRECLEAR_PROBE", "VPD_STAGE106_MMC3_CHR_PROBE"):
        env[var] = "0"
    env["VPD_STAGE107_BG_PIXEL_PROBE"] = "1" if enabled else "0"
    env["VPD_STAGE108_BG_FETCH_PROBE"] = "1" if enabled else "0"
    command = [str(Path(binary).resolve()), "--newppu", "1", "--sound", "0",
               "--opengl", "0", "--no-config", "1", str(rom.resolve())]
    log = folder / "native.log"
    with log.open("wb") as stream:
        proc = subprocess.Popen(command, cwd=folder, env=env,
                                stdout=stream, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL)
        until = time.monotonic() + (timeout if enabled else 2.0)
        try:
            while time.monotonic() < until:
                time.sleep(0.1)
                output = log.read_text(encoding="utf8", errors="replace")
                if enabled and MARKER in output and PIXEL_MARKER in output:
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
    output = log.read_text(encoding="utf8", errors="replace")
    if not enabled:
        if MARKER in output or PIXEL_MARKER in output or not survived:
            raise FetchProofError("Disabled native PPU observers not clean")
        return None
    if MARKER not in output or PIXEL_MARKER not in output:
        raise FetchProofError("No paired native CHR fetch/pixel evidence: " +
                              categorize_exit(proc.returncode, output))
    return verify_fetch(output), verify_pixels(output)


def run(binary, private_folder):
    with tempfile.TemporaryDirectory(dir=private_folder) as location:
        folder = Path(location)
        rom0, rom1 = folder / "bank0.nes", folder / "bank1.nes"
        make_rom(rom0, 0)
        make_rom(rom1, 1)
        blank_fetch, blank_pixel = execute(binary, rom0, folder / "blank")
        full_fetch, full_pixel = execute(binary, rom1, folder / "filled")
        execute(binary, rom1, folder / "disabled", enabled=False)
        verdict = verify_pair(blank_fetch, full_fetch, blank_pixel, full_pixel)
    print(
        "STAGE108_NATIVE_CHR_FETCH_FRAMEBUFFER_PASS "
        "native_fceux=yes synthetic_mapper4_only=yes reads_each=8192 "
        "bank0_zero=%d bank1_ff=%d "
        "background_pattern_and_framebuffer_different=yes "
        "same_run_native_witness=yes disabled_control=clean "
        "original_game_chr_fetch_proven=no" %
        (blank_fetch["zero"], full_fetch["ff"])
    )
    return verdict


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_fceux", type=Path)
    parser.add_argument("private_temp", type=Path)
    args = parser.parse_args()
    run(args.native_fceux, args.private_temp)
