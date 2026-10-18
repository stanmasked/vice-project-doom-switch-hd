#!/usr/bin/env python3
"""Accept native same-frame MMC3 CHR transition and two distinct XBuf pixel windows."""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage110_synthetic_midframe_rom import make_rom
from run_stage100_fceux_synthetic_smoke import backend_settings, categorize_exit

MARKER = "VPD_STAGE110_NATIVE_MIDFRAME_CHR_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE110_NATIVE_MIDFRAME_CHR_PASS "
    r"writes=2 switch_sl=(\d+) pre_pixels=2048 post_pixels=2048 "
    r"pre_zero=(\d+) post_three=(\d+) "
    r"pre_fnv64=(\d+) post_fnv64=(\d+) invalid=(\d+) "
    r"same_native_frame=yes synthetic_only=yes original_game_raster_proven=no$",
    re.MULTILINE
)


class MidframeError(ValueError):
    pass


def verify_report(text):
    found = list(PATTERN.finditer(text))
    if len(found) != 1 or text.count(MARKER) != 1:
        raise MidframeError("Missing, malformed or duplicate same-frame PPU witness")
    switch_line, pre_zero, post_three, pre_hash, post_hash, invalid = (
        int(v) for v in found[0].groups())
    if not 40 <= switch_line <= 210 or invalid or pre_zero != 2048 or post_three != 2048:
        raise MidframeError("Wrong source line, bank pattern, or corrupted raster evidence")
    if not (0 <= pre_hash < 2**64 and 0 <= post_hash < 2**64 and pre_hash != post_hash):
        raise MidframeError("Final framebuffer byte samples did not change")
    return {"switch_source_scanline": switch_line,
            "pre_pixels": 2048, "post_pixels": 2048,
            "same_synthetic_frame_proven": True, "original_raster_proven": False}


def execute(binary, rom, folder, *, enabled=True, expect_switch=True, timeout=25.0):
    folder.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(backend_settings("xvfb", folder))
    for name in ("VPD_STAGE100_SYNTHETIC_SMOKE", "VPD_STAGE102_STATUS_PROBE",
                 "VPD_STAGE103_PPUSTATUS_READ_PROBE", "VPD_STAGE104_EVENT_ORDER_PROBE",
                 "VPD_STAGE105_PRECLEAR_PROBE", "VPD_STAGE106_MMC3_CHR_PROBE",
                 "VPD_STAGE107_BG_PIXEL_PROBE", "VPD_STAGE108_BG_FETCH_PROBE",
                 "VPD_STAGE109_CHR_TIMELINE_PROBE"):
        env[name] = "0"
    env["VPD_STAGE110_MIDFRAME_CHR_PROBE"] = "1" if enabled else "0"
    command = [str(Path(binary).resolve()), "--newppu", "1", "--sound", "0",
               "--opengl", "0", "--no-config", "1", str(rom.resolve())]
    log = folder / "native.log"
    positive = enabled and expect_switch
    with log.open("wb") as stream:
        proc = subprocess.Popen(command, cwd=folder, env=env,
                                stdout=stream, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL)
        deadline = time.monotonic() + (timeout if positive else 2.0)
        try:
            while time.monotonic() < deadline:
                time.sleep(0.1)
                output = log.read_text(encoding="utf8", errors="replace")
                if positive and MARKER in output:
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
    if not positive:
        if MARKER in output or not survived:
            raise MidframeError("Fixed-bank/disabled diagnostic control failed")
        return None
    if MARKER not in output:
        diagnostics = re.findall(r"VPD_STAGE110_DIAGNOSTIC [^\r\n]{0,180}", output)
        raise MidframeError("Missing native same-frame witness: " +
                            (diagnostics[-1] if diagnostics else categorize_exit(proc.returncode, output)))
    return verify_report(output)


def run(binary, temporary):
    with tempfile.TemporaryDirectory(dir=temporary) as location:
        work = Path(location)
        switch_rom, fixed_rom = work / "switch.nes", work / "fixed.nes"
        make_rom(switch_rom, switch=True)
        make_rom(fixed_rom, switch=False)
        result = execute(binary, switch_rom, work / "positive")
        execute(binary, fixed_rom, work / "fixed", expect_switch=False)
        execute(binary, switch_rom, work / "disabled", enabled=False)
    print("STAGE110_NATIVE_MIDFRAME_CHR_PROOF "
          "native_fceux=yes synthetic_mapper4_only=yes "
          "same_rendered_frame=yes pre_pixels=2048 post_pixels=2048 "
          "source_switch_sl=%d fixed_bank_control=clean disabled_probe_control=clean "
          "original_game_raster_proven=no" % result["switch_source_scanline"])
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_fceux", type=Path)
    parser.add_argument("private_temp", type=Path)
    args = parser.parse_args()
    run(args.native_fceux, args.private_temp)
