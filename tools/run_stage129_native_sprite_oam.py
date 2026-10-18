#!/usr/bin/env python3
"""Stage129 synthetic OAM sprite0 vs background XBuf proof in pinned FCEUX.

Six real ROM/PPU paths: front/behind on opaque BG, behind/front on zero
BG, zero sprite CHR and disabled sprite rendering. Observer-disabled
control must produce no native witness. No copyrighted source assets.
"""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage129_oam_sprite_rom import make_rom
from run_stage100_fceux_synthetic_smoke import backend_settings, categorize_exit

MARKER = "VPD_STAGE129_NATIVE_SPRITE_OAM_PASS"
REJECTED = "VPD_STAGE129_REJECTED_SPRITE_OAM"
PATTERN = re.compile(
    r"^VPD_STAGE129_NATIVE_SPRITE_OAM_PASS "
    r"bg=(opaque|transparent) sprite=(solid|transparent) "
    r"priority=(front|behind) mask=(enabled|disabled) "
    r"sl=(\d+) sample_x=64 samples=8 quadrant=(\d+) "
    r"sprite_pattern=(\d+) bg_pattern=(\d+) "
    r"sprite_visible=(yes|no) sprite0_hit=(yes|no) xbuf=(\d+) invalid=0 "
    r"actual_fceux_oam_and_xbuf=yes synthetic_only=yes "
    r"original_game_sprite_proven=no$", re.MULTILINE,
)
SCENARIOS = (
    ("opaque_front", True, True, False, True),
    ("opaque_behind", True, True, True, True),
    ("transparent_front", False, True, False, True),
    ("transparent_behind", False, True, True, True),
    ("zero_sprite", True, False, False, True),
    ("disabled_sprite_mask", True, True, False, False),
)


class SpriteNativeError(ValueError):
    pass


def verify(log, *, bg_opaque, sprite_opaque, behind, sprite_enabled):
    expected = (bg_opaque, sprite_opaque, behind, sprite_enabled)
    if any(type(v) is not bool for v in expected):
        raise SpriteNativeError("Unbounded sprite mode")
    if (not isinstance(log, str) or log.count(MARKER) != 1 or REJECTED in log):
        raise SpriteNativeError("Absent, duplicated or contradicted sprite proof")
    matches = list(PATTERN.finditer(log))
    if len(matches) != 1:
        raise SpriteNativeError("Malformed newppu OAM/XBuf certificate")
    bg, sp, prio, mask, sl, q, sp_pattern, bg_pattern, visible, hit, color = matches[0].groups()
    sl, q, sp_pattern, bg_pattern, color = map(
        int, (sl, q, sp_pattern, bg_pattern, color))
    expected_visible = sprite_opaque and sprite_enabled and (
        not behind or not bg_opaque)
    expected_hit = sprite_opaque and sprite_enabled and bg_opaque
    expected_color = (170 if expected_visible else
                      176 + q if bg_opaque else 143)
    if (bg != ("opaque" if bg_opaque else "transparent")
            or sp != ("solid" if sprite_opaque else "transparent")
            or prio != ("behind" if behind else "front")
            or mask != ("enabled" if sprite_enabled else "disabled")
            or not 120 <= sl <= 140 or not 0 <= q <= 3
            or sp_pattern != (3 if sprite_opaque else 0)
            or bg_pattern != (3 if bg_opaque else 0)
            or visible != ("yes" if expected_visible else "no")
            or hit != ("yes" if expected_hit else "no")
            or color != expected_color):
        raise SpriteNativeError("Sprite priority, CHR, OAM status or framebuffer contradiction")
    return {
        "quadrant": q, "scanline": sl, "xbuf": color,
        "sprite_visible": expected_visible, "sprite0_hit": expected_hit,
        "samples": 8, "original_game_sprite_proven": False,
    }


def execute(binary, rom, directory, *, bg_opaque=True, sprite_opaque=True,
            behind=False, sprite_enabled=True, enabled=True, timeout=35):
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
    env["VPD_STAGE124_QUADRANT_PROBE"] = "0"
    env["VPD_STAGE129_SPRITE_PROBE"] = "1" if enabled else "0"
    env["VPD_STAGE129_BG"] = "opaque" if bg_opaque else "transparent"
    env["VPD_STAGE129_SPRITE"] = "solid" if sprite_opaque else "transparent"
    env["VPD_STAGE129_PRIORITY"] = "behind" if behind else "front"
    env["VPD_STAGE129_MASK"] = "enabled" if sprite_enabled else "disabled"
    env.pop("VPD_STAGE126_TARGET_QUADRANT", None)
    env.pop("VPD_STAGE127_BACKDROP", None)
    cmd = [str(Path(binary).resolve()), "--newppu", "1", "--sound", "0",
           "--opengl", "0", "--no-config", "1", str(Path(rom).resolve())]
    log_path = directory / "native.log"
    with log_path.open("wb") as output:
        proc = subprocess.Popen(cmd, cwd=directory, env=env, stdout=output,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        deadline = time.monotonic() + (timeout if enabled else 2.0)
        active = False
        try:
            while time.monotonic() < deadline:
                time.sleep(.1)
                log = log_path.read_text(encoding="utf8", errors="replace")
                if enabled and (MARKER in log or REJECTED in log):
                    break
                if proc.poll() is not None:
                    break
            active = proc.poll() is None
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=4)
    log = log_path.read_text(encoding="utf8", errors="replace")
    if not enabled:
        if not active or MARKER in log or REJECTED in log:
            raise SpriteNativeError("Disabled observer: early exit or false evidence")
        return None
    try:
        return verify(log, bg_opaque=bg_opaque,
                      sprite_opaque=sprite_opaque, behind=behind,
                      sprite_enabled=sprite_enabled)
    except SpriteNativeError as exc:
        rejected = re.findall(r"VPD_STAGE129_REJECTED_SPRITE_OAM [^\r\n]{0,210}", log)
        raise SpriteNativeError(
            str(exc) + ": " + (rejected[-1] if rejected else
                              categorize_exit(proc.returncode, log))) from exc


def verify_sweep(items):
    if (not isinstance(items, list) or
            [name for name, _ in items] != [s[0] for s in SCENARIOS]):
        raise SpriteNativeError("Missing or reordered sprite experiment")
    for (_, *modes), (_, evidence) in zip(SCENARIOS, items):
        bg, sp, behind, enabled = modes
        if (evidence.get("samples") != 8 or
                evidence.get("sprite_visible") !=
                (sp and enabled and (not behind or not bg)) or
                evidence.get("sprite0_hit") != (bg and sp and enabled) or
                evidence.get("original_game_sprite_proven") is not False):
            raise SpriteNativeError("Sprite evidence incomplete")
    return {"scenarios": len(items), "pixel_samples": len(items) * 8,
            "sprite0_hit_opaque": True, "native_sprite_pixels_proven": True,
            "original_game_sprite_proven": False}


def run(binary, temp):
    with tempfile.TemporaryDirectory(dir=temp) as dirname:
        root = Path(dirname)
        observed = []
        for name, bg, sp, behind, mask in SCENARIOS:
            rom = root / (name + ".nes")
            make_rom(rom, bg_opaque=bg, sprite_opaque=sp,
                     behind=behind, sprite_enabled=mask)
            outcome = execute(binary, rom, root / name, bg_opaque=bg,
                              sprite_opaque=sp, behind=behind,
                              sprite_enabled=mask)
            observed.append((name, outcome))
        control = root / "opaque_front.nes"
        execute(binary, control, root / "disabled_observer", enabled=False)
    result = verify_sweep(observed)
    print("STAGE129_NATIVE_SPRITE0_BG_PRIORITY_PROOF "
          "native_fceux=yes synthetic_mapper4_only=yes "
          "scenarios=6 samples=48 sprite0_hit_opaque=yes "
          "behind_opaque_hidden=yes behind_zero_bg_visible=yes "
          "transparent_sprite_hidden=yes disabled_sprite_mask_hidden=yes "
          "disabled_observer_control=clean "
          "original_game_sprite_proven=no")
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("native_fceux", type=Path)
    cli.add_argument("private_temp", type=Path)
    args = cli.parse_args()
    run(args.native_fceux, args.private_temp)
