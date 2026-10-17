#!/usr/bin/env python3
"""Verify paired synthetic $2005 writes and two raster changes in pinned FCEUX."""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage110_synthetic_midframe_rom import make_rom
from run_stage100_fceux_synthetic_smoke import backend_settings, categorize_exit
from run_stage110_native_midframe import MARKER as XBUF, verify_report as verify_xbuf

FINES = (1, 3, 5, 7)
MARKER = "VPD_STAGE118_NATIVE_TWO_SCROLL_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE118_NATIVE_TWO_SCROLL_PASS "
    r"first_fine=(\d+) second_fine=(\d+) coarse_first=0 coarse_second=1 "
    r"first_sl=(\d+) first_x=(\d+) second_sl=(\d+) second_x=(\d+) "
    r"first_after_x=(\d+) second_after_x=(\d+) "
    r"first_pixels=64 second_pixels=64 next_pixels=16 "
    r"shifted_first=64 shifted_second=64 "
    r"same_synthetic_frame=yes source_clock_only=yes "
    r"original_game_coarse_scroll_proven=no$", re.MULTILINE
)


class TwoScrollError(ValueError):
    pass


def verify_report(log, first, *, xbuf=None):
    matches = list(PATTERN.finditer(log))
    if len(matches) != 1 or log.count(MARKER) != 1:
        raise TwoScrollError("Missing, duplicate or forged native paired-scroll result")
    f, g, s1, x1, s2, x2, a1, a2 = map(int, matches[0].groups())
    if (f != first or first not in FINES or g != 8-first or
            not 40 <= s1 <= 210 or not s1 < s2 <= s1+5 or
            not 4 <= x1 <= 175 or not 4 <= x2 <= 175 or
            not x1 < a1 <= x1+16 or not x2 < a2 <= x2+16):
        raise TwoScrollError("Invalid coarse/fine write timing or raster coordinates")
    if xbuf is not None and (xbuf.get("switch_source_scanline") != s1 or
                            xbuf.get("same_synthetic_frame_proven") is not True or
                            xbuf.get("original_raster_proven") is not False):
        raise TwoScrollError("Paired scroll witness not bound to source framebuffer")
    return {"first_fine": f, "second_fine": g,
            "first_source_scanline": s1, "first_x": x1,
            "second_source_scanline": s2, "second_x": x2,
            "first_after_x": a1, "second_after_x": a2,
            "coarse_change_write_observed": True,
            "original_game_coarse_scroll_proven": False}


def verify_sweep(records):
    if len(records) != len(FINES) or [v for v, _ in records] != list(FINES):
        raise TwoScrollError("Missing, duplicated or reordered CPU scroll phases")
    sl1 = [r["first_source_scanline"] for _, r in records]
    sl2 = [r["second_source_scanline"] for _, r in records]
    if len(set(sl1)) != 1 or len(set(sl2)) != 1:
        raise TwoScrollError("Write phases did not occur on shared source rows")
    for fine, r in records:
        if (r["first_fine"] != fine or r["second_fine"] != 8-fine or
                r["coarse_change_write_observed"] is not True or
                r["original_game_coarse_scroll_proven"] is not False):
            raise TwoScrollError("Incorrect observed paired-register values")
    return {"first_line": sl1[0], "second_line": sl2[0],
            "first_x": [r["first_x"] for _, r in records],
            "second_x": [r["second_x"] for _, r in records]}


def execute(binary, rom, folder, *, first, enabled=True, positive=True, timeout=25.0):
    folder.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(backend_settings("xvfb", folder))
    for var in (
        "VPD_STAGE100_SYNTHETIC_SMOKE", "VPD_STAGE102_STATUS_PROBE",
        "VPD_STAGE103_PPUSTATUS_READ_PROBE", "VPD_STAGE104_EVENT_ORDER_PROBE",
        "VPD_STAGE105_PRECLEAR_PROBE", "VPD_STAGE106_MMC3_CHR_PROBE",
        "VPD_STAGE107_BG_PIXEL_PROBE", "VPD_STAGE108_BG_FETCH_PROBE",
        "VPD_STAGE109_CHR_TIMELINE_PROBE", "VPD_STAGE111_BG_TILE_PROBE",
        "VPD_STAGE113_BG_PREFETCH_PROBE", "VPD_STAGE114_PLANE_PAIR_PROBE",
        "VPD_STAGE115_SCANLINE_CARRY_PROBE", "VPD_STAGE116_FINE_SCROLL_PROBE",
        "VPD_STAGE117_DYNAMIC_SCROLL_PROBE",
    ):
        env[var] = "0"
    env["VPD_STAGE110_MIDFRAME_CHR_PROBE"] = "1" if enabled else "0"
    env["VPD_STAGE118_TWO_SCROLL_PROBE"] = "1" if enabled else "0"
    env["VPD_STAGE118_FIRST_FINE"] = str(first)
    command = [str(Path(binary).resolve()), "--newppu", "1", "--sound", "0",
               "--opengl", "0", "--no-config", "1", str(rom.resolve())]
    out = folder / "native.log"
    with out.open("wb") as sink:
        proc = subprocess.Popen(command, cwd=folder, env=env,
                                stdin=subprocess.DEVNULL, stdout=sink,
                                stderr=subprocess.STDOUT)
        deadline = time.monotonic() + (timeout if positive else 2.0)
        try:
            while time.monotonic() < deadline:
                time.sleep(.1)
                log = out.read_text(encoding="utf8", errors="replace")
                if positive and MARKER in log and XBUF in log:
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
    log = out.read_text(encoding="utf8", errors="replace")
    if not positive:
        if MARKER in log or XBUF in log or not survived:
            raise TwoScrollError("Fixed bank / disabled observer control was not clean")
        return None
    if log.count(MARKER) != 1 or log.count(XBUF) != 1:
        diag = re.findall(r"VPD_STAGE118_REJECTED_TWO_SCROLLS [^\r\n]{0,200}", log)
        raise TwoScrollError("Missing paired native scroll and XBuf witness: " +
                             (diag[-1] if diag else
                              categorize_exit(proc.returncode, log)))
    return verify_report(log, first, xbuf=verify_xbuf(log))


def run(binary, temp):
    with tempfile.TemporaryDirectory(dir=temp) as name:
        root = Path(name)
        observations = []
        for fine in FINES:
            rom = root / ("fine_%d.nes" % fine)
            make_rom(rom, dynamic_fine_scroll=fine,
                     second_dynamic_scroll=16-fine)
            observed = execute(binary, rom, root / ("observed_%d" % fine),
                               first=fine)
            observations.append((fine, observed))
        fixed = root / "fixed.nes"
        make_rom(fixed, switch=False, dynamic_fine_scroll=3,
                 second_dynamic_scroll=13)
        execute(binary, fixed, root / "fixed_control", first=3, positive=False)
        execute(binary, root / "fine_7.nes", root / "disabled",
                first=7, enabled=False, positive=False)
    proof = verify_sweep(observations)
    print(
        "STAGE118_NATIVE_TWO_SCROLL_SOURCE_PROOF native_fceux=yes "
        "synthetic_mapper4_only=yes first_fines=1,3,5,7 "
        "second_fines=7,5,3,1 second_coarse=1 first_sl=%d second_sl=%d "
        "first_write_x=%s second_write_x=%s "
        "same_line_first_pixels_each=64 same_line_second_pixels_each=64 "
        "next_line_pixels_each=16 paired_real_xbuf_each=yes "
        "fixed_bank_control=clean disabled_control=clean "
        "original_game_coarse_scroll_proven=no" %
        (proof["first_line"], proof["second_line"],
         ",".join(map(str, proof["first_x"])),
         ",".join(map(str, proof["second_x"])))
    )
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_fceux", type=Path)
    parser.add_argument("private_temp", type=Path)
    opts = parser.parse_args()
    run(opts.native_fceux, opts.private_temp)
