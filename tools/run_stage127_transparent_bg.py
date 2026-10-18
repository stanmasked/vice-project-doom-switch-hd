#!/usr/bin/env python3
"""Stage127 real FCEUX universal background when CHR pixel pattern is zero.

Tests both backdrop colors plus an opaque-CHR negative control against
actual buffered E4 attribute reads and final XBuf. Generated ROM only.
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

MARKER = "VPD_STAGE127_NATIVE_TRANSPARENT_BG_PASS"
REJECTED = "VPD_STAGE127_REJECTED_TRANSPARENT_BG"
PATTERN = re.compile(
    r"^VPD_STAGE127_NATIVE_TRANSPARENT_BG_PASS "
    r"backdrop=(\d+) samples=16,16,16,16 quadrant_indices=0,4,8,12 "
    r"xbuf=(\d+),(\d+),(\d+),(\d+) invalid=0 "
    r"actual_fceux_xbuf=yes synthetic_only=yes "
    r"original_game_transparency_proven=no$", re.MULTILINE,
)
REJECT_PATTERN = re.compile(
    r"^VPD_STAGE127_REJECTED_TRANSPARENT_BG "
    r"backdrop=(\d+) invalid=(\d+) "
    r"xbuf=(\d+),(\d+),(\d+),(\d+) "
    r"samples=16,16,16,16 synthetic_only=yes$", re.MULTILINE,
)


class TransparentBGError(ValueError):
    pass


def verify(log, backdrop):
    if (type(backdrop) is not int or backdrop not in (15, 29)
            or not isinstance(log, str) or log.count(MARKER) != 1
            or REJECTED in log):
        raise TransparentBGError("Absent, contradicted or duplicated backdrop witness")
    matches = list(PATTERN.finditer(log))
    if len(matches) != 1:
        raise TransparentBGError("Malformed native transparent CHR report")
    observed_backdrop, *colors = map(int, matches[0].groups())
    expected = (128 | backdrop,) * 4
    if observed_backdrop != backdrop or tuple(colors) != expected:
        raise TransparentBGError("Attribute quadrant leaked into universal backdrop")
    return {"backdrop": backdrop, "xbuf": list(colors),
            "samples": 64, "original_game_transparency_proven": False}


def verify_opaque_rejection(log):
    if not isinstance(log, str) or log.count(REJECTED) != 1 or MARKER in log:
        raise TransparentBGError("Opaque negative control did not explicitly reject")
    matches = list(REJECT_PATTERN.finditer(log))
    if len(matches) != 1:
        raise TransparentBGError("Malformed native opaque rejection")
    backdrop, invalid, *colors = map(int, matches[0].groups())
    if (backdrop != 15 or invalid <= 0 or
            tuple(colors) != (176, 177, 178, 179)):
        raise TransparentBGError("Rejected control did not actually render opaque CHR")
    return {"opaque_rejected": True, "invalid": invalid, "xbuf": colors}


def verify_pair(first, second, negative):
    if (first.get("backdrop") != 15 or second.get("backdrop") != 29
            or first.get("xbuf") != [143] * 4
            or second.get("xbuf") != [157] * 4
            or first.get("samples") != 64 or second.get("samples") != 64
            or first.get("original_game_transparency_proven") is not False
            or second.get("original_game_transparency_proven") is not False
            or negative.get("opaque_rejected") is not True):
        raise TransparentBGError("Incomplete two-backdrop native proof")
    return {"samples": 128, "xbuf_before": [143] * 4,
            "xbuf_after": [157] * 4,
            "unchanged_attribute_quadrants": 4,
            "original_game_transparency_proven": False}


def execute(binary, rom, directory, backdrop, *, expect_rejection=False,
            timeout=35):
    if type(backdrop) is not int or backdrop not in (15, 29):
        raise TransparentBGError("Unsupported synthetic background color")
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
    env["VPD_STAGE127_BACKDROP"] = str(backdrop)
    env.pop("VPD_STAGE126_TARGET_QUADRANT", None)
    cmd = [str(Path(binary).resolve()), "--newppu", "1", "--sound", "0",
           "--opengl", "0", "--no-config", "1", str(Path(rom).resolve())]
    path = directory / "native.log"
    with path.open("wb") as sink:
        proc = subprocess.Popen(cmd, cwd=directory, env=env, stdout=sink,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        try:
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                time.sleep(0.1)
                log = path.read_text(encoding="utf8", errors="replace")
                if (MARKER in log or REJECTED in log
                        or proc.poll() is not None):
                    break
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=4)
    log = path.read_text(encoding="utf8", errors="replace")
    try:
        return verify_opaque_rejection(log) if expect_rejection else verify(log, backdrop)
    except TransparentBGError as exc:
        details = re.findall(r"VPD_STAGE127_REJECTED_TRANSPARENT_BG [^\r\n]{0,180}", log)
        raise TransparentBGError(
            str(exc) + ": " +
            (details[-1] if details else categorize_exit(proc.returncode, log))) from exc


def run(binary, temp):
    with tempfile.TemporaryDirectory(dir=temp) as name:
        root = Path(name)
        base = root / "zero_chr_15.nes"
        changed = root / "zero_chr_29.nes"
        opaque = root / "opaque_chr.nes"
        make_rom(base, transparent_chr=True)
        make_rom(changed, transparent_chr=True, backdrop_color=0x1D)
        make_rom(opaque)
        first = execute(binary, base, root / "backdrop15", 15)
        second = execute(binary, changed, root / "backdrop29", 29)
        negative = execute(binary, opaque, root / "opaque", 15,
                           expect_rejection=True)
    summary = verify_pair(first, second, negative)
    print("STAGE127_NATIVE_UNIVERSAL_BACKDROP_PROOF "
          "native_fceux=yes synthetic_mapper4_only=yes "
          "attribute_byte=E4 quadrants=4 "
          "indices=0,4,8,12 samples=%d "
          "background15_xbuf=143,143,143,143 "
          "background29_xbuf=157,157,157,157 "
          "opaque_chr_negative=rejected "
          "original_game_transparency_proven=no" %
          summary["samples"])
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("native_fceux", type=Path)
    p.add_argument("private_temp", type=Path)
    a = p.parse_args()
    run(a.native_fceux, a.private_temp)
