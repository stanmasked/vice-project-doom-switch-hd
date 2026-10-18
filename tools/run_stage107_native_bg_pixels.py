#!/usr/bin/env python3
"""Two controlled CHR banks compared through native FCEUX final framebuffer bytes."""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage107_synthetic_chr_pixel_rom import make_rom
from run_stage100_fceux_synthetic_smoke import backend_settings, categorize_exit

MARKER = "VPD_STAGE107_NATIVE_BG_PIXEL_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE107_NATIVE_BG_PIXEL_PASS sampled=32768 "
    r"bg_zero=(\d+) bg_nonzero=(\d+) final_fnv64=(\d+) invalid=(\d+) "
    r"synthetic_only=yes original_pixel_proof=no$", re.MULTILINE)


class PixelProofError(ValueError):
    pass


def verify_report(output):
    matches = list(PATTERN.finditer(output))
    if len(matches) != 1 or output.count(MARKER) != 1:
        raise PixelProofError("Missing, duplicate or malformed final-pixel proof")
    zero, nonzero, checksum, invalid = map(int, matches[0].groups())
    if invalid or zero + nonzero != 32768 or not (0 <= checksum < 2**64):
        raise PixelProofError("Native rendered pixel aggregate inconsistent")
    return {"sampled": 32768, "bg_zero": zero, "bg_nonzero": nonzero,
            "final_fnv64": checksum, "original_pixel_proof": False}


def verify_pair(a, b):
    if a["sampled"] != 32768 or b["sampled"] != 32768:
        raise PixelProofError("Missing samples")
    if a["bg_nonzero"] > 1024:
        raise PixelProofError("Blank bank generated nonzero background bits")
    if b["bg_nonzero"] < 24576:
        raise PixelProofError("Filled bank did not reach newppu rendering")
    if a["final_fnv64"] == b["final_fnv64"]:
        raise PixelProofError("Actual framebuffer bytes did not change")
    return True


def execute(binary, rom, folder, *, enabled=True, timeout=25):
    folder.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(backend_settings("xvfb", folder))
    for tag in ("VPD_STAGE100_SYNTHETIC_SMOKE", "VPD_STAGE102_STATUS_PROBE",
                "VPD_STAGE103_PPUSTATUS_READ_PROBE", "VPD_STAGE104_EVENT_ORDER_PROBE",
                "VPD_STAGE105_PRECLEAR_PROBE", "VPD_STAGE106_MMC3_CHR_PROBE"):
        env[tag] = "0"
    env["VPD_STAGE107_BG_PIXEL_PROBE"] = "1" if enabled else "0"
    command = [str(Path(binary).resolve()), "--newppu", "1", "--sound", "0",
               "--opengl", "0", "--no-config", "1", str(rom.resolve())]
    log = folder / "native.log"
    with log.open("wb") as stream:
        proc = subprocess.Popen(command, env=env, cwd=folder,
                                stdout=stream, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL)
        deadline = time.monotonic() + (timeout if enabled else 2)
        try:
            while time.monotonic() < deadline:
                time.sleep(0.1)
                output = log.read_text(encoding="utf8", errors="replace")
                if enabled and MARKER in output:
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
        if MARKER in output or not survived:
            raise PixelProofError("Disabled observer control not clean")
        return None
    if MARKER not in output:
        raise PixelProofError("No FCEUX final-pixel observation: " +
                              categorize_exit(proc.returncode, output))
    return verify_report(output)


def run(binary, temp):
    with tempfile.TemporaryDirectory(dir=temp) as name:
        folder = Path(name)
        a_rom = folder / "empty_bank.nes"
        b_rom = folder / "filled_bank.nes"
        make_rom(a_rom, 0)
        make_rom(b_rom, 1)
        a = execute(binary, a_rom, folder / "bank0")
        b = execute(binary, b_rom, folder / "bank1")
        execute(binary, b_rom, folder / "disabled", enabled=False)
        verify_pair(a, b)
    print("STAGE107_SYNTHETIC_CHR_FRAMEBUFFER_PASS "
          "native_fceux=yes synthetic_mapper4_only=yes "
          "sampled_each=32768 bank0_nonzero=%d bank1_nonzero=%d "
          "final_framebuffer_different=yes disabled_control=clean "
          "original_game_pixels_proven=no" % (a["bg_nonzero"], b["bg_nonzero"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_fceux", type=Path)
    parser.add_argument("temporary_folder", type=Path)
    args = parser.parse_args()
    run(args.native_fceux, args.temporary_folder)
