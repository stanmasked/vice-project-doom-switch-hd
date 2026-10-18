#!/usr/bin/env python3
"""Native dynamic $2005 test: post-register same-line BG source changes.

Only generated iNES Mapper 4 ROMs, real pinned FCEUX and opt-in provenance.
"""
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

VALUES = (1, 3, 5, 7)
MARKER = "VPD_STAGE117_NATIVE_DYNAMIC_SCROLL_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE117_NATIVE_DYNAMIC_SCROLL_PASS "
    r"old_fine=0 new_fine=(\d+) write_sl=(\d+) write_x=(\d+) "
    r"first_after_x=(\d+) same_line_samples=64 next_line_samples=16 "
    r"shifted_samples=64 first_lag=(\d+) source_clock_only=yes "
    r"same_native_frame=yes synthetic_only=yes "
    r"original_game_midframe_scroll_proven=no$", re.MULTILINE
)


class DynamicScrollError(ValueError):
    pass


def verify_report(log, value, *, xbuf=None):
    found = list(PATTERN.finditer(log))
    if len(found) != 1 or log.count(MARKER) != 1:
        raise DynamicScrollError("Missing, duplicate or malformed native write-to-raster witness")
    fine, source_sl, write_x, first_x, lag = map(int, found[0].groups())
    if (fine != value or fine not in VALUES or
            not 40 <= source_sl <= 210 or
            not 4 <= write_x <= 175 or
            not write_x < first_x <= write_x + 16 or
            not 0 <= lag <= 1000000):
        raise DynamicScrollError("Write position, target or source-clock lag impossible")
    if xbuf is not None and (
            xbuf.get("switch_source_scanline") != source_sl or
            xbuf.get("same_synthetic_frame_proven") is not True or
            xbuf.get("original_raster_proven") is not False):
        raise DynamicScrollError("Dynamic scroll not bound to real same-run XBuf proof")
    return {"new_fine": fine, "write_source_scanline": source_sl,
            "write_screen_x": write_x, "first_updated_screen_x": first_x,
            "source_first_lag": lag, "same_native_frame_proven": True,
            "original_game_midframe_scroll_proven": False}


def verify_sweep(records):
    if (len(records) != len(VALUES) or
            [value for value, _ in records] != list(VALUES)):
        raise DynamicScrollError("Missing, duplicated or misordered dynamic scroll trial")
    lines = [result["write_source_scanline"] for _, result in records]
    writes = [result["write_screen_x"] for _, result in records]
    if len(set(lines)) != 1 or any(abs(v - writes[0]) > 16 for v in writes):
        raise DynamicScrollError("Trials switch on different source rows or large clock drift")
    if any(record["original_game_midframe_scroll_proven"] is not False
           for _, record in records):
        raise DynamicScrollError("Original game scroll evidence forged")
    return {"target_values": list(VALUES), "source_sl": lines[0],
            "observed_write_x": writes, "original_game_midframe_scroll_proven": False}


def native(binary, rom, folder, *, target, enabled=True, positive=True, timeout=25):
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
    ):
        env[var] = "0"
    env["VPD_STAGE110_MIDFRAME_CHR_PROBE"] = "1" if enabled else "0"
    env["VPD_STAGE117_DYNAMIC_SCROLL_PROBE"] = "1" if enabled else "0"
    env["VPD_STAGE117_EXPECT_FINE"] = str(target)
    command = [str(Path(binary).resolve()), "--newppu", "1", "--sound", "0",
               "--opengl", "0", "--no-config", "1", str(rom.resolve())]
    log_path = folder / "native.log"
    with log_path.open("wb") as out:
        proc = subprocess.Popen(command, cwd=folder, env=env,
                                stdout=out, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL)
        end = time.monotonic() + (timeout if positive else 2)
        try:
            while time.monotonic() < end:
                time.sleep(.1)
                log = log_path.read_text(encoding="utf8", errors="replace")
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
    log = log_path.read_text(encoding="utf8", errors="replace")
    if not positive:
        if MARKER in log or XBUF in log or not survived:
            raise DynamicScrollError("Fixed-bank or disabled probe control produced success")
        return None
    if log.count(MARKER) != 1 or log.count(XBUF) != 1:
        failures = re.findall(
            r"VPD_STAGE117_REJECTED_DYNAMIC_SCROLL [^\r\n]{0,180}", log)
        raise DynamicScrollError("Missing native paired scroll/XBuf witness: " +
                                 (failures[-1] if failures else
                                  categorize_exit(proc.returncode, log)))
    return verify_report(log, target, xbuf=verify_xbuf(log))


def run(binary, temp):
    with tempfile.TemporaryDirectory(dir=temp) as location:
        root = Path(location)
        observed = []
        for value in VALUES:
            rom = root / ("x_%d.nes" % value)
            make_rom(rom, dynamic_fine_scroll=value)
            observed.append((value, native(binary, rom,
                                           root / ("native_%d" % value),
                                           target=value)))
        fixed = root / "fixed.nes"
        make_rom(fixed, switch=False, dynamic_fine_scroll=VALUES[1])
        native(binary, fixed, root / "fixed_control",
               target=VALUES[1], positive=False)
        native(binary, root / ("x_%d.nes" % VALUES[-1]), root / "disabled",
               target=VALUES[-1], enabled=False, positive=False)
    result = verify_sweep(observed)
    print("STAGE117_NATIVE_DYNAMIC_SCROLL_SOURCE_PROOF "
          "native_fceux=yes synthetic_mapper4_only=yes targets=1,3,5,7 "
          "write_sl=%d write_x=%s first_after_x=%s "
          "samples_same_line_each=64 samples_next_line_each=16 "
          "paired_native_xbuf_each=yes fixed_bank_control=clean "
          "disabled_control=clean original_game_midframe_scroll_proven=no" %
          (result["source_sl"],
           ",".join(str(r["write_screen_x"]) for _, r in observed),
           ",".join(str(r["first_updated_screen_x"]) for _, r in observed)))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_fceux", type=Path)
    parser.add_argument("private_temp", type=Path)
    args = parser.parse_args()
    run(args.native_fceux, args.private_temp)
