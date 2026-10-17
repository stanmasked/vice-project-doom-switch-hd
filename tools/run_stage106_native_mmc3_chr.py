#!/usr/bin/env python3
"""Stage106 real FCEUX synthetic MMC3 $8001 CHR-write/window correlation.

Only aggregate source-level CHR register writes: no ROM pixels or fetch proof.
"""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage106_synthetic_mmc3_rom import make_mapper4_chr_toggle_rom
from run_stage100_fceux_synthetic_smoke import backend_settings, categorize_exit

MARKER = "VPD_STAGE106_NATIVE_MMC3_CHR_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE106_NATIVE_MMC3_CHR_PASS writes=4096 "
    r"changed=(\d+) within_source_window=(\d+) outside_source_window=(\d+) "
    r"after_cpu_high_read=(\d+) lag_min=(\d+) lag_max=(\d+) invalid=(\d+) "
    r"source_only=yes chr_pixel_causality_proven=no$",
    re.MULTILINE,
)


class Mmc3ProbeError(ValueError):
    pass


def verify_chr_write_report(output):
    matches = list(PATTERN.finditer(output))
    if len(matches) != 1 or output.count(MARKER) != 1:
        raise Mmc3ProbeError("Missing, duplicate, or malformed source-level MMC3 proof")
    changed, within, outside, after_high, lag_min, lag_max, invalid = (
        int(v) for v in matches[0].groups())
    if invalid:
        raise Mmc3ProbeError("Invalid MMC3 source-write timeline observations")
    if not (0 < changed < 4096):
        raise Mmc3ProbeError("No genuine alternating CHR register values")
    if not (0 < within < 4096 and 0 < outside < 4096 and
            within + outside == 4096):
        raise Mmc3ProbeError("Missing or inconsistent source-frame window classification")
    if not (0 < after_high <= within):
        raise Mmc3ProbeError("No MMC3 write correlated after a high $2002 read")
    if not (0 <= lag_min <= lag_max <= 1000000):
        raise Mmc3ProbeError("Invalid native internal-tick lag distribution")
    return {
        "native_chr_register_writes": 4096,
        "changed_chr_register_values": changed,
        "writes_during_source_window": within,
        "writes_outside_source_window": outside,
        "writes_after_high_cpu_read": after_high,
        "lag_min_internal_ppu_ticks": lag_min,
        "lag_max_internal_ppu_ticks": lag_max,
        "source_event_correlation_verified": True,
        "chr_bank_to_pixel_causality_verified": False,
        "original_first_level_geometry_verified": False,
    }


def execute(binary, rom, folder, *, enabled, timeout=24):
    folder.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(backend_settings("xvfb", folder))
    for name in ("VPD_STAGE100_SYNTHETIC_SMOKE", "VPD_STAGE102_STATUS_PROBE",
                 "VPD_STAGE103_PPUSTATUS_READ_PROBE",
                 "VPD_STAGE105_PRECLEAR_PROBE"):
        env[name] = "0"
    # Stage104 event-order state must track source windows even without
    # its own 16384-read output; separate Stage106 witness is required.
    env["VPD_STAGE104_EVENT_ORDER_PROBE"] = "1"
    env["VPD_STAGE106_MMC3_CHR_PROBE"] = "1" if enabled else "0"
    cmd = [str(Path(binary).resolve()), "--newppu", "1",
           "--sound", "0", "--opengl", "0", "--no-config", "1",
           str(rom.resolve())]
    path = folder / "execution.log"
    with path.open("wb") as stream:
        proc = subprocess.Popen(cmd, cwd=folder, env=env,
                                stdin=subprocess.DEVNULL,
                                stdout=stream, stderr=subprocess.STDOUT)
        end = time.monotonic() + (timeout if enabled else 2)
        try:
            while time.monotonic() < end:
                time.sleep(0.1)
                output = path.read_text(encoding="utf8", errors="replace")
                if enabled and MARKER in output:
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
    output = path.read_text(encoding="utf8", errors="replace")
    if not enabled:
        if MARKER in output:
            raise Mmc3ProbeError("Disabled native CHR probe emitted positive proof")
        if not survived:
            raise Mmc3ProbeError("Disabled MMC3 control exited early: " +
                                 categorize_exit(proc.returncode, output))
        return None
    if MARKER not in output:
        raise Mmc3ProbeError("No native MMC3 CHR write observation: " +
                             categorize_exit(proc.returncode, output))
    return verify_chr_write_report(output)


def run(binary, temporary):
    with tempfile.TemporaryDirectory(dir=temporary) as name:
        folder = Path(name)
        rom = folder / "original_synthetic_mapper4.nes"
        make_mapper4_chr_toggle_rom(rom)
        proof = execute(binary, rom, folder / "enabled", enabled=True)
        execute(binary, rom, folder / "disabled", enabled=False)
    print("STAGE106_FCEUX_NATIVE_MMC3_CHR_PROOF "
          "synthetic_mapper4_only=yes disabled_probe_control=clean "
          "writes=4096 "
          f"changed={proof['changed_chr_register_values']} "
          f"within={proof['writes_during_source_window']} "
          f"outside={proof['writes_outside_source_window']} "
          f"after_high_read={proof['writes_after_high_cpu_read']} "
          f"lag_min={proof['lag_min_internal_ppu_ticks']} "
          f"lag_max={proof['lag_max_internal_ppu_ticks']} "
          "ppu_fetch_visibility_proven=no original_level_geometry_proven=no")
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_fceux", type=Path)
    parser.add_argument("private_runner_directory", type=Path)
    args = parser.parse_args()
    run(args.native_fceux, args.private_runner_directory)


if __name__ == "__main__":
    main()
