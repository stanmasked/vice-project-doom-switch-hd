#!/usr/bin/env python3
"""Stage116 native fine-scroll carry test: four $2005 phases and controls."""
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
    MARKER as PIXEL_MARKER, verify_report as verify_xbuf,
)

SCROLLS = (0, 1, 3, 7)
MARKER = "VPD_STAGE116_NATIVE_FINE_SCROLL_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE116_NATIVE_FINE_SCROLL_PASS "
    r"fine_scroll=(\d+) source_switch_sl=104 first_new_sl=105 "
    r"samples=128 old_pixels=72 new_pixels=56 "
    r"slot0_pixels=(\d+) slot1_pixels=(\d+) "
    r"lag_min=(\d+) lag_max=(\d+) "
    r"invalid=0 same_native_frame=yes synthetic_only=yes "
    r"original_game_scroll_proven=no$", re.MULTILINE,
)


class FineScrollError(ValueError):
    pass


def verify_report(log, expected):
    found = list(PATTERN.finditer(log))
    if len(found) != 1 or log.count(MARKER) != 1:
        raise FineScrollError("Missing, duplicate or malformed native fine-scroll marker")
    scroll, first, second, lag_min, lag_max = map(int, found[0].groups())
    if (scroll != expected or scroll not in SCROLLS or
            first != 16 * (8 - scroll) or second != 16 * scroll or
            not 0 < lag_min <= lag_max <= 1000000):
        raise FineScrollError("Incorrect source tile transition or carry timing")
    return {"fine_scroll": scroll, "slot0": first, "slot1": second,
            "lag_min": lag_min, "lag_max": lag_max,
            "original_game_scroll_proven": False}


def validate_sweep(records):
    if len(records) != len(SCROLLS) or [v[0] for v in records] != list(SCROLLS):
        raise FineScrollError("Invalid phase order or missing experiment")
    for scroll, report in records:
        if (report["fine_scroll"] != scroll or
                report["slot0"] != 16 * (8 - scroll) or
                report["slot1"] != 16 * scroll or
                report["original_game_scroll_proven"] is not False):
            raise FineScrollError("Unpaired scroll-to-source-row witness")
    return {"scroll_values": list(SCROLLS),
            "slot1_counts": [v["slot1"] for _, v in records],
            "original_game_scroll_proven": False}


def execute(binary, rom, folder, *, scroll, enabled=True, positive=True, timeout=25.0):
    folder.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(backend_settings("xvfb", folder))
    for var in ("VPD_STAGE100_SYNTHETIC_SMOKE", "VPD_STAGE102_STATUS_PROBE",
                "VPD_STAGE103_PPUSTATUS_READ_PROBE", "VPD_STAGE104_EVENT_ORDER_PROBE",
                "VPD_STAGE105_PRECLEAR_PROBE", "VPD_STAGE106_MMC3_CHR_PROBE",
                "VPD_STAGE107_BG_PIXEL_PROBE", "VPD_STAGE108_BG_FETCH_PROBE",
                "VPD_STAGE109_CHR_TIMELINE_PROBE", "VPD_STAGE111_BG_TILE_PROBE",
                "VPD_STAGE113_BG_PREFETCH_PROBE", "VPD_STAGE114_PLANE_PAIR_PROBE",
                "VPD_STAGE115_SCANLINE_CARRY_PROBE"):
        env[var] = "0"
    env["VPD_STAGE110_MIDFRAME_CHR_PROBE"] = "1" if enabled else "0"
    env["VPD_STAGE116_FINE_SCROLL_PROBE"] = "1" if enabled else "0"
    env["VPD_STAGE116_EXPECT_FINE_SCROLL"] = str(scroll)
    cmd = [str(Path(binary).resolve()), "--newppu", "1", "--sound", "0",
           "--opengl", "0", "--no-config", "1", str(rom.resolve())]
    path = folder / "native.log"
    with path.open("wb") as output:
        proc = subprocess.Popen(cmd, cwd=folder, env=env, stdin=subprocess.DEVNULL,
                                stdout=output, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + (timeout if positive else 2.0)
        try:
            while time.monotonic() < deadline:
                time.sleep(0.1)
                log = path.read_text(encoding="utf8", errors="replace")
                if positive and MARKER in log and PIXEL_MARKER in log:
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
    log = path.read_text(encoding="utf8", errors="replace")
    if not positive:
        if MARKER in log or PIXEL_MARKER in log or not survived:
            raise FineScrollError("Fixed-bank/disabled-observer negative run failed")
        return None
    if log.count(MARKER) != 1 or log.count(PIXEL_MARKER) != 1:
        diagnostics = re.findall(
            r"VPD_STAGE116_REJECTED_FINE_SCROLL [^\r\n]{0,160}", log)
        raise FineScrollError("Missing paired native framebuffer/fine scroll: " +
                              (diagnostics[-1] if diagnostics else
                               categorize_exit(proc.returncode, log)))
    xbuf = verify_xbuf(log)
    if xbuf["switch_source_scanline"] != 104:
        raise FineScrollError("Wrong bank transition line in native PPU")
    return verify_report(log, scroll)


def run(binary, temp):
    with tempfile.TemporaryDirectory(dir=temp) as location:
        root = Path(location)
        observations = []
        for scroll in SCROLLS:
            rom = root / ("fine_%d.nes" % scroll)
            make_rom(rom, fine_scroll=scroll)
            records = execute(binary, rom, root / ("native_%d" % scroll),
                              scroll=scroll)
            observations.append((scroll, records))
        fixed = root / "fixed.nes"
        make_rom(fixed, switch=False, fine_scroll=SCROLLS[2])
        execute(binary, fixed, root / "fixed", scroll=SCROLLS[2], positive=False)
        execute(binary, root / ("fine_%d.nes" % SCROLLS[-1]),
                root / "disabled", scroll=SCROLLS[-1],
                enabled=False, positive=False)
    result = validate_sweep(observations)
    print("STAGE116_NATIVE_FINE_SCROLL_SOURCE_PROOF "
          "native_fceux=yes synthetic_mapper4_only=yes "
          "scrolls=0,1,3,7 samples_each=128 first_new_sl=105 "
          "slot0_counts=%s slot1_counts=%s "
          "same_run_real_xbuf_each=yes fixed_bank_control=clean "
          "disabled_control=clean original_game_scroll_proven=no" %
          (",".join(str(item[1]["slot0"]) for item in observations),
           ",".join(str(item[1]["slot1"]) for item in observations)))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("native_fceux", type=Path)
    p.add_argument("private_temp", type=Path)
    args = p.parse_args()
    run(args.native_fceux, args.private_temp)
