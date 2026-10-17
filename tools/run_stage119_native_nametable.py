#!/usr/bin/env python3
"""Confirm real rendered, differently-patterned nametable IDs after coarse X write.

Requires 4 independent FCEUX runs and two independent negative controls;
never relies on a marker from uniform-CHR Stage110 for this experiment.
"""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage119_nametable_rom import make_rom
from run_stage100_fceux_synthetic_smoke import backend_settings, categorize_exit

FINES = (1, 3, 5, 7)
MARKER = "VPD_STAGE119_NATIVE_NAMETABLE_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE119_NATIVE_NAMETABLE_PASS "
    r"fine1=(\d+) fine2=(\d+) coarse1=0 coarse2=1 "
    r"write_sl1=(\d+) write_sl2=(\d+) "
    r"sample_sl1=(\d+) sample_sl2=(\d+) "
    r"nametable0_x0=0 nametable1_x0=1 "
    r"pattern0_x0=0 pattern1_x0=3 "
    r"first_color=(\d+) second_color=(\d+) "
    r"samples_per_row=16 odd_first=(\d+) odd_second=(\d+) "
    r"invalid=0 real_fceux_xbuf=yes synthetic_only=yes "
    r"original_game_coarse_scroll_proven=no$", re.MULTILINE,
)


class TileIdentityError(ValueError):
    pass


def verify_report(log, fine):
    found = list(PATTERN.finditer(log))
    if len(found) != 1 or log.count(MARKER) != 1:
        raise TileIdentityError("Absent/duplicated/forged nametable-to-XBuf evidence")
    f, g, first, second, sl1, sl2, color1, color2, odd1, odd2 = map(
        int, found[0].groups())
    if (fine not in FINES or f != fine or g != 8-fine or
            not 40 <= first <= 210 or second != first+1 or
            sl1 != first+1 or sl2 != second+1 or
            color1 == color2 or color1 > 255 or color2 > 255 or
            not 0 < odd1 < 16 or not 0 < odd2 < 16):
        raise TileIdentityError("Tile identity, framebuffer color or scroll origin inconsistent")
    return {"fine_first": f, "fine_second": g, "source_line": first,
            "second_write_line": second, "first_xbuf_color": color1,
            "second_xbuf_color": color2, "odd_first": odd1,
            "odd_second": odd2, "original_game_coarse_scroll_proven": False}


def verify_sweep(records):
    if len(records) != len(FINES) or [f for f, _ in records] != list(FINES):
        raise TileIdentityError("Missing or reordered nametable experiment")
    lines = [result["source_line"] for _, result in records]
    if len(set(lines)) != 1:
        raise TileIdentityError("Different source rows for synthetic scroll controls")
    for fine, item in records:
        if (item["fine_first"] != fine or item["fine_second"] != 8-fine or
                item["original_game_coarse_scroll_proven"] is not False):
            raise TileIdentityError("Invalid original-game provenance or scroll phases")
    return {"first_sl": lines[0], "phases": list(FINES)}


def execute(binary, rom, directory, *, fine, enabled=True, positive=True,
            timeout=25):
    directory.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(backend_settings("xvfb", directory))
    for var in (
        "VPD_STAGE100_SYNTHETIC_SMOKE", "VPD_STAGE102_STATUS_PROBE",
        "VPD_STAGE103_PPUSTATUS_READ_PROBE", "VPD_STAGE104_EVENT_ORDER_PROBE",
        "VPD_STAGE105_PRECLEAR_PROBE", "VPD_STAGE106_MMC3_CHR_PROBE",
        "VPD_STAGE107_BG_PIXEL_PROBE", "VPD_STAGE108_BG_FETCH_PROBE",
        "VPD_STAGE109_CHR_TIMELINE_PROBE", "VPD_STAGE111_BG_TILE_PROBE",
        "VPD_STAGE113_BG_PREFETCH_PROBE", "VPD_STAGE114_PLANE_PAIR_PROBE",
        "VPD_STAGE115_SCANLINE_CARRY_PROBE", "VPD_STAGE116_FINE_SCROLL_PROBE",
        "VPD_STAGE117_DYNAMIC_SCROLL_PROBE", "VPD_STAGE118_TWO_SCROLL_PROBE",
    ):
        env[var] = "0"
    # Stage110 is needed for the original CPU write epoch and scanline
    # tracker, not its all-FF-bank positive result (the tile CHR now differs).
    env["VPD_STAGE110_MIDFRAME_CHR_PROBE"] = "1" if enabled else "0"
    env["VPD_STAGE119_NAMETABLE_PROBE"] = "1" if enabled else "0"
    env["VPD_STAGE119_FIRST_FINE"] = str(fine)
    command = [str(Path(binary).resolve()), "--newppu", "1", "--sound", "0",
               "--opengl", "0", "--no-config", "1", str(rom.resolve())]
    output = directory / "native.log"
    with output.open("wb") as sink:
        proc = subprocess.Popen(command, cwd=directory, env=env,
                                stdout=sink, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL)
        limit = time.monotonic() + (timeout if positive else 2.0)
        try:
            while time.monotonic() < limit:
                time.sleep(0.1)
                log = output.read_text(encoding="utf8", errors="replace")
                if positive and MARKER in log:
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
    log = output.read_text(encoding="utf8", errors="replace")
    if not positive:
        if MARKER in log or not alive:
            raise TileIdentityError("Uniform-CHR or disabled-observer control not clean")
        return None
    if log.count(MARKER) != 1:
        details = re.findall(
            r"VPD_STAGE119_REJECTED_NAMETABLE [^\r\n]{0,200}", log)
        raise TileIdentityError("Missing real nametable CHR/XBuf witness: " +
                                (details[-1] if details else
                                 categorize_exit(proc.returncode, log)))
    return verify_report(log, fine)


def run(binary, temp):
    with tempfile.TemporaryDirectory(dir=temp) as name:
        root = Path(name)
        measured = []
        for fine in FINES:
            rom = root / ("distinct_%d.nes" % fine)
            make_rom(rom, first=fine)
            measured.append((fine, execute(
                binary, rom, root / ("session_%d" % fine), fine=fine)))
        control = root / "identical.nes"
        make_rom(control, first=3, differentiated=False)
        execute(binary, control, root / "uniform_chr", fine=3, positive=False)
        execute(binary, root / "distinct_7.nes", root / "disabled",
                fine=7, enabled=False, positive=False)
    result = verify_sweep(measured)
    print(
        "STAGE119_NATIVE_COARSE_NAMETABLE_SOURCE_PROOF "
        "native_fceux=yes synthetic_mapper4_only=yes phases=1,3,5,7 "
        "first_write_sl=%d second_write_sl=%d "
        "first_tile_nt=0 second_tile_nt=1 "
        "first_pixel_pattern=0 second_pixel_pattern=3 "
        "real_xbuf_colors_distinct_each=yes "
        "first_colors=%s second_colors=%s samples_each_row=16 "
        "uniform_chr_control=clean disabled_probe_control=clean "
        "original_game_coarse_scroll_proven=no" %
        (result["first_sl"], result["first_sl"]+1,
         ",".join(str(x["first_xbuf_color"]) for _, x in measured),
         ",".join(str(x["second_xbuf_color"]) for _, x in measured))
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_fceux", type=Path)
    parser.add_argument("private_temp", type=Path)
    args = parser.parse_args()
    run(args.native_fceux, args.private_temp)
