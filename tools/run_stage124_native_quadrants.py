#!/usr/bin/env python3
"""Stage124 real FCEUX native 4-quadrant palette-to-XBuf acceptance.

Only generated synthetic Mapper-4 ROMs. Never publishes XBuf frame, ROM
bytes, palette memory, original-game assets or per-pixel traces.
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

MARKER = "VPD_STAGE124_NATIVE_QUADRANTS_PASS"
REJECTED = "VPD_STAGE124_REJECTED_QUADRANTS"
REJECTION_PATTERN = re.compile(
    r"^VPD_STAGE124_REJECTED_QUADRANTS invalid=(\\d+) "
    r"bad_attribute=(\\d+) bad_color=(\\d+) "
    r"colors=(\\d+),(\\d+),(\\d+),(\\d+) "
    r"samples=16,16,16,16 synthetic_only=yes$", re.MULTILINE,
)
PATTERN = re.compile(
    r"^VPD_STAGE124_NATIVE_QUADRANTS_PASS "
    r"groups=4 samples=16,16,16,16 indices=3,7,11,15 "
    r"xbuf_colors=(\d+),(\d+),(\d+),(\d+) "
    r"raw_attribute=E4 invalid=0 "
    r"actual_fceux_xbuf=yes synthetic_only=yes "
    r"original_game_palette_proven=no$", re.MULTILINE,
)


class QuadrantNativeError(ValueError):
    pass


def verify(log):
    if not isinstance(log, str) or REJECTED in log or log.count(MARKER) != 1:
        raise QuadrantNativeError("Missing, rejected or duplicated native palette proof")
    matches = list(PATTERN.finditer(log))
    if len(matches) != 1:
        raise QuadrantNativeError("Invalid native FCEUX quadrant certificate")
    colors = tuple(map(int, matches[0].groups()))
    if colors != (176, 177, 178, 179):
        raise QuadrantNativeError("Wrong native XBuf colors or palette order")
    return {"xbuf_colors": list(colors), "samples": 64, "groups": 4,
            "original_game_palette_proven": False}


def verify_rejection(log, cause):
    if cause not in ("attribute", "palette") or not isinstance(log, str):
        raise QuadrantNativeError("Invalid rejection control")
    if log.count(REJECTED) != 1 or MARKER in log:
        raise QuadrantNativeError("Missing, duplicated or positive negative control")
    matches = list(REJECTION_PATTERN.finditer(log))
    if len(matches) != 1:
        raise QuadrantNativeError("Malformed native rejection evidence")
    invalid, bad_attribute, bad_color, *colors = map(int, matches[0].groups())
    if (invalid <= 0 or tuple(colors) != (176, 176, 176, 176) or
            bad_color <= 0 or
            (cause == "attribute" and bad_attribute <= 0) or
            (cause == "palette" and bad_attribute != 0)):
        raise QuadrantNativeError("Negative control did not expose its causal mismatch")
    return {"cause": cause, "invalid": invalid, "bad_attribute": bad_attribute,
            "bad_color": bad_color, "xbuf_colors": colors,
            "native_rejection_observed": True}


def execute(binary, rom, directory, *, enabled=True, positive=True,
            expect_rejection=None, timeout=35):
    if expect_rejection is not None and (
            expect_rejection not in ("attribute", "palette") or positive or not enabled):
        raise ValueError("Expected rejection requires an enabled negative control")
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
    env["VPD_STAGE124_QUADRANT_PROBE"] = "1" if enabled else "0"
    cmd = [str(Path(binary).resolve()), "--newppu", "1", "--sound", "0",
           "--opengl", "0", "--no-config", "1", str(Path(rom).resolve())]
    log_path = directory / "native.log"
    with log_path.open("wb") as handle:
        proc = subprocess.Popen(cmd, cwd=directory, env=env, stdout=handle,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        limit = time.monotonic() + (timeout if positive or expect_rejection else 2)
        alive = False
        try:
            while time.monotonic() < limit:
                time.sleep(0.1)
                log = log_path.read_text(encoding="utf8", errors="replace")
                if (positive or expect_rejection) and (MARKER in log or REJECTED in log):
                    break
                if proc.poll() is not None:
                    break
            alive = proc.poll() is None
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=4)
    log = log_path.read_text(encoding="utf8", errors="replace")
    if not positive:
        if MARKER in log or not alive:
            raise QuadrantNativeError("False-positive or early-exit negative control")
        if expect_rejection:
            return verify_rejection(log, expect_rejection)
        if REJECTED in log:
            raise QuadrantNativeError("Disabled observer emitted a rejection")
        return None
    try:
        return verify(log)
    except QuadrantNativeError as exc:
        details = re.findall(r"VPD_STAGE124_REJECTED_QUADRANTS [^\r\n]{0,250}", log)
        raise QuadrantNativeError(str(exc) + ": " +
                                  (details[-1] if details else
                                   categorize_exit(proc.returncode, log))) from exc


def run(binary, temp):
    with tempfile.TemporaryDirectory(dir=temp) as rootdir:
        root = Path(rootdir)
        positive = root / "four_quadrants.nes"
        make_rom(positive)
        witness = execute(binary, positive, root / "positive")
        attr_control = root / "uniform_attributes.nes"
        make_rom(attr_control, attribute=0)
        attr_failure = execute(
            binary, attr_control, root / "uniform_attr",
            positive=False, expect_rejection="attribute")
        palette_control = root / "uniform_palette.nes"
        make_rom(palette_control, distinct_palette=False)
        palette_failure = execute(
            binary, palette_control, root / "uniform_pal",
            positive=False, expect_rejection="palette")
        execute(binary, positive, root / "disabled", enabled=False, positive=False)
    print(
        "STAGE125_NATIVE_NEGATIVE_CAUSAL_PROOF "
        "native_fceux=yes synthetic_mapper4_only=yes "
        "uniform_attr_rejected=yes uniform_palette_rejected=yes "
        "attribute_failures=%d palette_color_failures=%d "
        "disabled_observer_control=clean "
        "original_game_palette_proven=no" %
        (attr_failure["bad_attribute"], palette_failure["bad_color"])
    )
    print(
        "STAGE124_NATIVE_FOUR_QUADRANT_COLOR_PROOF "
        "native_fceux=yes synthetic_mapper4_only=yes groups=4 "
        "samples=16,16,16,16 indices=3,7,11,15 "
        "xbuf_colors=176,177,178,179 "
        "uniform_attribute_control=clean uniform_palette_control=clean "
        "disabled_observer_control=clean "
        "original_game_palette_proven=no"
    )
    return witness


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_fceux", type=Path)
    parser.add_argument("private_temp", type=Path)
    args = parser.parse_args()
    run(args.native_fceux, args.private_temp)
