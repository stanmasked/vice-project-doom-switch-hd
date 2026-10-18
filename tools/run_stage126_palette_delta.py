#!/usr/bin/env python3
"""Stage126 native paired palette-only single-quadrant intervention.

Five positive FCEUX sessions (baseline and four one-color variants) plus
an explicit false-intervention negative control. Never exports ROM or frames.
"""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage124_native_quadrant_rom import make_rom
from run_stage100_fceux_synthetic_smoke import backend_settings, categorize_exit
from run_stage124_native_quadrants import execute as baseline_execute

MARKER = "VPD_STAGE126_NATIVE_PALETTE_DELTA_PASS"
REJECTED = "VPD_STAGE126_REJECTED_PALETTE_DELTA"
BASE = (176, 177, 178, 179)
PATTERN = re.compile(
    r"^VPD_STAGE126_NATIVE_PALETTE_DELTA_PASS "
    r"target=(\d) samples=16,16,16,16 indices=3,7,11,15 "
    r"base=176,177,178,179 observed=(\d+),(\d+),(\d+),(\d+) "
    r"changed_quadrants=1 invalid=0 actual_fceux_xbuf=yes "
    r"synthetic_only=yes original_game_palette_proven=no$", re.MULTILINE,
)
REJECT_PATTERN = re.compile(
    r"^VPD_STAGE126_REJECTED_PALETTE_DELTA "
    r"target=(\d) invalid=(\d+) "
    r"observed=(\d+),(\d+),(\d+),(\d+) "
    r"samples=16,16,16,16 synthetic_only=yes$", re.MULTILINE,
)


class PaletteDeltaError(ValueError):
    pass


def expected_colors(target):
    if type(target) is not int or target not in range(4):
        raise PaletteDeltaError("Expected one target quadrant 0..3")
    colors = list(BASE)
    colors[target] = 180 + target
    return tuple(colors)


def verify_delta_report(log, target):
    expected = expected_colors(target)
    if not isinstance(log, str) or log.count(MARKER) != 1 or REJECTED in log:
        raise PaletteDeltaError("Absent, duplicate or contradicted delta certificate")
    found = list(PATTERN.finditer(log))
    if len(found) != 1:
        raise PaletteDeltaError("Malformed native one-quadrant certificate")
    values = tuple(map(int, found[0].groups()))
    if values[0] != target or values[1:] != expected:
        raise PaletteDeltaError("Native XBuf intervention moved incorrect quadrants")
    return {"target": target, "observed": list(expected), "samples": 64,
            "changed_quadrants": 1, "original_game_palette_proven": False}


def verify_negative(log, target):
    expected_colors(target)
    if not isinstance(log, str) or log.count(REJECTED) != 1 or MARKER in log:
        raise PaletteDeltaError("Missing, duplicate or falsely successful negative control")
    found = list(REJECT_PATTERN.finditer(log))
    if len(found) != 1:
        raise PaletteDeltaError("Malformed native rejected intervention")
    t, invalid, *colors = map(int, found[0].groups())
    if t != target or invalid <= 0 or tuple(colors) != BASE:
        raise PaletteDeltaError("Negative control did not preserve unchanged palette")
    return {"target": target, "rejected": True, "invalid": invalid,
            "observed": colors}


def verify_sweep(items, baseline):
    if (not isinstance(items, list) or len(items) != 4 or
            [t for t, _ in items] != list(range(4)) or
            not isinstance(baseline, dict) or
            baseline.get("xbuf_colors") != list(BASE) or
            baseline.get("original_game_palette_proven") is not False):
        raise PaletteDeltaError("Missing or mismatched paired FCEUX baseline")
    for target, report in items:
        if (report.get("target") != target or
                report.get("observed") != list(expected_colors(target)) or
                report.get("samples") != 64 or
                report.get("changed_quadrants") != 1 or
                report.get("original_game_palette_proven") is not False):
            raise PaletteDeltaError("Incomplete quadrant-specific counterfactual")
    return {"targeted_interventions": 4, "native_pixel_samples": 256,
            "unchanged_quadrants_each": 3, "original_game_palette_proven": False}


def execute_delta(binary, rom, directory, target, *, expect_rejection=False,
                  timeout=35):
    expected_colors(target)
    directory.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(backend_settings("xvfb", directory))
    for key in (
        "VPD_STAGE100_SYNTHETIC_SMOKE", "VPD_STAGE102_STATUS_PROBE",
        "VPD_STAGE103_PPUSTATUS_READ_PROBE", "VPD_STAGE104_EVENT_ORDER_PROBE",
        "VPD_STAGE105_PRECLEAR_PROBE", "VPD_STAGE106_MMC3_CHR_PROBE",
        "VPD_STAGE107_BG_PIXEL_PROBE", "VPD_STAGE108_BG_FETCH_PROBE",
        "VPD_STAGE109_CHR_TIMELINE_PROBE", "VPD_STAGE111_BG_TILE_PROBE",
        "VPD_STAGE113_BG_PREFETCH_PROBE", "VPD_STAGE114_PLANE_PAIR_PROBE",
        "VPD_STAGE115_SCANLINE_CARRY_PROBE", "VPD_STAGE116_FINE_SCROLL_PROBE",
        "VPD_STAGE117_DYNAMIC_SCROLL_PROBE", "VPD_STAGE118_TWO_SCROLL_PROBE",
        "VPD_STAGE119_NAMETABLE_PROBE",
    ):
        env[key] = "0"
    env["VPD_STAGE110_MIDFRAME_CHR_PROBE"] = "1"
    env["VPD_STAGE124_QUADRANT_PROBE"] = "1"
    env["VPD_STAGE126_TARGET_QUADRANT"] = str(target)
    cmd = [str(Path(binary).resolve()), "--newppu", "1", "--sound", "0",
           "--opengl", "0", "--no-config", "1", str(Path(rom).resolve())]
    log_path = directory / "native.log"
    with log_path.open("wb") as sink:
        proc = subprocess.Popen(cmd, cwd=directory, env=env, stdout=sink,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline:
                time.sleep(0.1)
                log = log_path.read_text(encoding="utf8", errors="replace")
                if MARKER in log or REJECTED in log or proc.poll() is not None:
                    break
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=4)
    log = log_path.read_text(encoding="utf8", errors="replace")
    try:
        return (verify_negative(log, target) if expect_rejection
                else verify_delta_report(log, target))
    except PaletteDeltaError as e:
        reasons = re.findall(r"VPD_STAGE126_REJECTED_PALETTE_DELTA [^\r\n]{0,200}", log)
        raise PaletteDeltaError(
            str(e) + ": " + (reasons[-1] if reasons else
                            categorize_exit(proc.returncode, log))) from e


def run(binary, temp):
    with tempfile.TemporaryDirectory(dir=temp) as dirname:
        root = Path(dirname)
        source = root / "baseline.nes"
        make_rom(source)
        baseline = baseline_execute(binary, source, root / "baseline")
        observations = []
        for target in range(4):
            rom = root / ("mutate_palette_%d.nes" % target)
            make_rom(rom, targeted_quadrant=target)
            result = execute_delta(binary, rom, root / ("delta_%d" % target), target)
            observations.append((target, result))
        # No palette change despite claiming target zero: must REJECT after
        # actual FCEUX sampling, not just time out without a PASS.
        negative = execute_delta(binary, source, root / "unchanged_control",
                                 target=0, expect_rejection=True)
    summary = verify_sweep(observations, baseline)
    if negative["invalid"] <= 0:
        raise PaletteDeltaError("Native counterfactual rejection not supported")
    print("STAGE126_NATIVE_SINGLE_PALETTE_ENTRY_DELTA_PROOF "
          "native_fceux=yes synthetic_mapper4_only=yes targets=0,1,2,3 "
          "baseline_xbuf=176,177,178,179 "
          "changed_xbuf=180,181,182,183 "
          "samples=%d unchanged_quadrants_each=3 "
          "unchanged_rom_negative=rejected "
          "original_game_palette_proven=no" %
          summary["native_pixel_samples"])
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("native_fceux", type=Path)
    p.add_argument("private_temp", type=Path)
    a = p.parse_args()
    run(a.native_fceux, a.private_temp)
