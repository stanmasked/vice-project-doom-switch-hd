#!/usr/bin/env python3
"""Verify paired buffered BG tile and XBuf evidence in pinned native FCEUX."""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage110_synthetic_midframe_rom import make_rom
from run_stage100_fceux_synthetic_smoke import backend_settings, categorize_exit
from run_stage110_native_midframe import (
    MARKER as PIXEL_MARKER, verify_report as verify_pixels,
)

MARKER = "VPD_STAGE111_NATIVE_TILE_BOUNDARY_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE111_NATIVE_TILE_BOUNDARY_PASS "
    r"switch_sl=(\d+) last_rendered_xt=(\d+) "
    r"pre_tiles=128 pre_zero=128 transient_old=(\d+) "
    r"first_new_sl=(\d+) first_new_xt=(\d+) "
    r"new_tiles=128 new_ff=128 regressions=0 invalid=0 "
    r"same_rendered_frame=yes synthetic_only=yes "
    r"original_game_tile_proven=no$", re.MULTILINE,
)


class TileProofError(ValueError):
    pass


def verify_report(output, *, stage110=None):
    matched = list(PATTERN.finditer(output))
    if len(matched) != 1 or output.count(MARKER) != 1:
        raise TileProofError("Missing, malformed or duplicate native tile proof")
    switch_sl, switch_xt, transient, first_sl, first_xt = map(
        int, matched[0].groups())
    if (not 40 <= switch_sl <= 210 or switch_xt >= 32 or
            transient > 64 or not switch_sl <= first_sl <= switch_sl + 3
            or first_xt >= 32):
        raise TileProofError("Invalid buffered-tile transition coordinates")
    if stage110 is not None and (
            stage110.get("switch_source_scanline") != switch_sl or
            stage110.get("same_synthetic_frame_proven") is not True):
        raise TileProofError("Unbound native XBuf witness")
    return {"switch_source_scanline": switch_sl,
            "last_rendered_xt": switch_xt, "transient_old_tiles": transient,
            "first_new_source_scanline": first_sl, "first_new_xt": first_xt,
            "same_buffered_tile_frame_proven": True,
            "original_game_tile_proven": False}


def run_native(binary, rom, folder, *, enabled=True, positive=True, timeout=25.0, prefetch=False, plane_pairs=False):
    folder.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(backend_settings("xvfb", folder))
    for tag in ("VPD_STAGE100_SYNTHETIC_SMOKE", "VPD_STAGE102_STATUS_PROBE",
                "VPD_STAGE103_PPUSTATUS_READ_PROBE", "VPD_STAGE104_EVENT_ORDER_PROBE",
                "VPD_STAGE105_PRECLEAR_PROBE", "VPD_STAGE106_MMC3_CHR_PROBE",
                "VPD_STAGE107_BG_PIXEL_PROBE", "VPD_STAGE108_BG_FETCH_PROBE",
                "VPD_STAGE109_CHR_TIMELINE_PROBE"):
        env[tag] = "0"
    env["VPD_STAGE110_MIDFRAME_CHR_PROBE"] = "1" if enabled else "0"
    env["VPD_STAGE111_BG_TILE_PROBE"] = "1" if enabled else "0"
    env["VPD_STAGE113_BG_PREFETCH_PROBE"] = "1" if enabled and prefetch else "0"
    env["VPD_STAGE114_PLANE_PAIR_PROBE"] = "1" if enabled and plane_pairs else "0"
    cmd = [str(Path(binary).resolve()), "--newppu", "1", "--sound", "0",
           "--opengl", "0", "--no-config", "1", str(rom.resolve())]
    log = folder / "native.log"
    with log.open("wb") as stream:
        proc = subprocess.Popen(cmd, cwd=folder, env=env,
                                stdin=subprocess.DEVNULL, stdout=stream,
                                stderr=subprocess.STDOUT)
        end = time.monotonic() + (timeout if positive else 2)
        try:
            while time.monotonic() < end:
                time.sleep(0.1)
                output = log.read_text(encoding="utf8", errors="replace")
                if positive and MARKER in output and PIXEL_MARKER in output and (not prefetch or "VPD_STAGE113_NATIVE_PREFETCH_PASS" in output) and (not plane_pairs or "VPD_STAGE114_NATIVE_PLANE_PAIR_PASS" in output):
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
        if MARKER in output or PIXEL_MARKER in output or "VPD_STAGE113_NATIVE_PREFETCH_PASS" in output or "VPD_STAGE114_NATIVE_PLANE_PAIR_PASS" in output or not survived:
            raise TileProofError("Disabled/fixed-bank native control not clean")
        return None
    if output.count(MARKER) != 1 or output.count(PIXEL_MARKER) != 1:
        diagnostics = re.findall(
            r"VPD_STAGE111_REJECTED_TILE_BOUNDARY [^\r\n]{0,180}", output)
        raise TileProofError("Missing paired native tile/XBuf witness: " +
                             (diagnostics[-1] if diagnostics else
                              categorize_exit(proc.returncode, output)))
    witness = verify_report(output, stage110=verify_pixels(output))
    if prefetch:
        if output.count("VPD_STAGE113_NATIVE_PREFETCH_PASS") != 1:
            raise TileProofError("Absent or repeated native prefetch proof")
        return witness, output
    if plane_pairs:
        if output.count("VPD_STAGE114_NATIVE_PLANE_PAIR_PASS") != 1:
            raise TileProofError("Missing or repeated native split-plane audit")
        return witness, output
    return witness


def run(binary, private_dir):
    with tempfile.TemporaryDirectory(dir=private_dir) as name:
        folder = Path(name)
        switch, fixed = folder / "switch.nes", folder / "fixed.nes"
        make_rom(switch, switch=True)
        make_rom(fixed, switch=False)
        result = run_native(binary, switch, folder / "positive")
        run_native(binary, fixed, folder / "fixed", positive=False)
        run_native(binary, switch, folder / "disabled",
                   enabled=False, positive=False)
    print("STAGE111_NATIVE_BUFFERED_TILE_PROOF native_fceux=yes "
          "synthetic_mapper4_only=yes old_tiles=128 new_tiles=128 "
          "transient_old=%d switch_sl=%d first_new_sl=%d first_new_xt=%d "
          "paired_xbuf_same_run=yes fixed_bank_control=clean "
          "disabled_control=clean original_game_tiles_proven=no" %
          (result["transient_old_tiles"], result["switch_source_scanline"],
           result["first_new_source_scanline"], result["first_new_xt"]))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_fceux", type=Path)
    parser.add_argument("private_temp", type=Path)
    opts = parser.parse_args()
    run(opts.native_fceux, opts.private_temp)
