#!/usr/bin/env python3
"""Aggregate PRIVATE FCEUX PPUMASK A/B observations without exporting pixels.

The 4-frame captures may include proprietary gameplay. All paths and pixel
contents remain local. A stable changed-row mask is not a calibrated CPU
scanline: emu.registerafter() has no independently known PPU-dot origin.
"""
import argparse
import csv
import json
from pathlib import Path

from audit_private_ppumask_ab import (
    PIXELS, PPM_HEADER, PALETTE_SIZE, EXPECTED_SIZE, _read, _directory, audit
)


def _mask(first, second, channels):
    if len(first) != len(second) or len(first) != PIXELS * channels:
        raise ValueError("invalid private screenshot mask dimensions")
    return bytes(1 if first[i * channels:(i + 1) * channels] !=
                 second[i * channels:(i + 1) * channels] else 0
                 for i in range(PIXELS))


def _private_file(path, limit=48 * 1024 * 1024):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= limit:
        raise ValueError("private trace absent, linked or oversized")
    return path


def _decimal(value, name):
    if (not isinstance(value, str) or not value.isascii() or
        not value.isdecimal() or value != str(int(value))):
        raise ValueError("noncanonical " + name)
    return int(value)


def _completion(path, expected_format, min_frame):
    result = {}
    for line in _private_file(path, 4096).read_text("ascii").splitlines():
        if "=" not in line:
            raise ValueError("malformed provenance marker")
        key, val = line.split("=", 1)
        if key in result:
            raise ValueError("duplicate provenance marker")
        result[key] = val
    if (result.get("format") != expected_format or
        result.get("rom_identity_verified") != "yes" or
        result.get("movie_readonly_verified") != "yes" or
        _decimal(result.get("frame_gaps", ""), "frame gap count") != 0 or
        _decimal(result.get("last_observed_frame", ""), "last frame") < min_frame or
        _decimal(result.get("first_observed_frame", ""), "first frame") not in (0, 1)):
        raise ValueError("private CPU trace identity or continuity unverified")


def _phases(targets, anchor_tsv, anchor_witness, cpu_tsv, cpu_witness):
    latest = max(targets)
    _completion(anchor_witness, "private_original_fceux_frame_anchor_v1", latest)
    _completion(cpu_witness, "private_stage155_cpu_sequence_v1", latest)
    anchors = {}
    with _private_file(anchor_tsv).open("r", encoding="ascii", newline="") as handle:
        rows = csv.DictReader(handle, delimiter="\t")
        if rows.fieldnames != ["frame", "cycle"]:
            raise ValueError("unexpected CPU frame-anchor schema")
        prior_frame, prior_cycle = -1, -1
        for count, item in enumerate(rows):
            if count >= 4000 or None in item or any(v is None for v in item.values()):
                raise ValueError("malformed frame-anchor trace")
            frame = _decimal(item["frame"], "anchor frame")
            cycle = _decimal(item["cycle"], "anchor CPU cycle")
            if frame <= prior_frame or cycle <= prior_cycle:
                raise ValueError("nonmonotonic frame anchors")
            anchors[frame] = cycle
            prior_frame, prior_cycle = frame, cycle
    wanted = set(targets)
    hits = {}
    prior_frame, prior_cycle = -1, -1
    with _private_file(cpu_tsv).open("r", encoding="ascii", newline="") as handle:
        rows = csv.DictReader(handle, delimiter="\t")
        if rows.fieldnames != ["frame", "cycle", "type", "address",
                               "value", "a", "x", "y", "p"]:
            raise ValueError("unexpected private CPU execution schema")
        for count, item in enumerate(rows):
            if count >= 500000 or None in item or any(v is None for v in item.values()):
                raise ValueError("malformed CPU instruction event")
            frame = _decimal(item["frame"], "instruction frame")
            cycle = _decimal(item["cycle"], "instruction cycle")
            if frame < prior_frame or cycle < prior_cycle:
                raise ValueError("CPU instruction clock/frames out of order")
            prior_frame, prior_cycle = frame, cycle
            if frame in wanted and item["type"] == "PC" and item["address"] == "E38E":
                if frame in hits:
                    raise ValueError("duplicate original PPUMASK instruction callback")
                hits[frame] = cycle
    samples = {}
    for frame in targets:
        if frame not in hits or frame - 1 not in anchors or frame not in anchors:
            raise ValueError("unpaired original PPUMASK instruction/frame clock")
        prev, now = anchors[frame - 1], anchors[frame]
        if not prev < hits[frame] < now:
            raise ValueError("CPU cycle clock epochs are inconsistent")
        samples[frame] = {
            "after_previous_frame_callback_cycles": hits[frame] - prev,
            "before_current_frame_callback_cycles": now - hits[frame],
        }
    return samples


def audit_series(manifest, *, anchor_tsv=None, anchor_witness=None,
                 cpu_tsv=None, cpu_witness=None):
    manifest = _private_file(manifest, 65536)
    records = json.loads(manifest.read_text("utf8"))
    if (not isinstance(records, list) or
        not 3 <= len(records) <= 20):
        raise ValueError("three to twenty distinct private experiments required")
    fields = {"frame", "original_dir", "probe_dir"}
    previous = -1
    signatures = []
    seen_dirs = set()
    results = []
    for record in records:
        if not isinstance(record, dict) or set(record) != fields:
            raise ValueError("unexpected private experiment manifest entry")
        target = record["frame"]
        if type(target) is not int or target <= previous or target < 300:
            raise ValueError("private experiment frame numbers must be sorted and distinct")
        previous = target
        original = _directory(record["original_dir"])
        probe = _directory(record["probe_dir"])
        for root in (original, probe):
            key = str(root.resolve())
            if key in seen_dirs:
                raise ValueError("private experiment capture directory reused")
            seen_dirs.add(key)
        result = audit(original, probe, target_frame=target)
        if result["changed_capture_frames"] != [target + 1]:
            raise ValueError("PPUMASK effect is not isolated to next captured frame")
        for entry in result["pixel_differences"]:
            if entry["frame"] != target + 1 and (entry["rgb_changed"]["pixels"] or
                                                 entry["palette_changed"]["pixels"]):
                raise ValueError("uncontrolled before/after-frame divergence")
        name = f"frame_{target + 1:06d}"
        rgb_a = _read(original / (name + ".ppm"), EXPECTED_SIZE)
        rgb_b = _read(probe / (name + ".ppm"), EXPECTED_SIZE)
        pal_a = _read(original / (name + ".pal.bin"), PALETTE_SIZE)
        pal_b = _read(probe / (name + ".pal.bin"), PALETTE_SIZE)
        rmask = _mask(rgb_a[len(PPM_HEADER):], rgb_b[len(PPM_HEADER):], 3)
        pmask = _mask(pal_a, pal_b, 1)
        if rmask != pmask:
            raise ValueError("RGB/palette spatial change masks disagree")
        rows = tuple(y for y in range(240)
                     if any(rmask[y * 256:(y + 1) * 256]))
        if not rows:
            raise ValueError("no effect in the diagnostic next-frame image")
        signatures.append(rows)
        results.append({
            "target_frame": target,
            "changed_capture_frame": target + 1,
            "rgb_and_palette_changed_pixel_count": sum(rmask),
            "changed_row_indices": list(rows),
            "explicit_cpu_accumulator_restore_witness_present":
                result["diagnostic_accumulator_restored_before_rts_verified"],
        })
    if len(set(signatures)) != 1:
        raise ValueError("different visible affected-row sets across experiments")
    params = (anchor_tsv, anchor_witness, cpu_tsv, cpu_witness)
    if any(p is not None for p in params):
        if any(p is None for p in params):
            raise ValueError("supply all four private CPU clock inputs")
        clocks = _phases([r["target_frame"] for r in results], *params)
        for item in results:
            item["cpu_instruction_clock"] = clocks[item["target_frame"]]
    phase = [r["cpu_instruction_clock"]["after_previous_frame_callback_cycles"]
             for r in results] if all("cpu_instruction_clock" in r for r in results) else []
    shared = list(signatures[0])
    return {
        "schema": "vpd_private_ppumask_four_case_repeatability_v1",
        "classification": "controlled emulator framebuffer response, not scanline timing",
        "case_count": len(results), "cases": results,
        "same_affected_row_set_in_every_case": True,
        "shared_affected_row_indices": shared,
        "shared_changed_row_min": min(shared),
        "shared_changed_row_max": max(shared),
        "rgb_pal_pixel_masks_identical_in_every_case": True,
        "all_cpu_accumulator_restoration_explicitly_witnessed":
            all(x["explicit_cpu_accumulator_restore_witness_present"] for x in results),
        "cross_run_cpu_cycle_phase_observed": bool(phase),
        "cpu_e38e_phase_spread_cycles": max(phase) - min(phase) if phase else None,
        "cpu_e38e_phase_min_cycles": min(phase) if phase else None,
        "cpu_e38e_phase_max_cycles": max(phase) if phase else None,
        "independent_ppu_dot_origin_calibration": False,
        "absolute_cpu_instruction_scanline_proven": False,
        "original_car_camera_speed_proven": False,
        "full_original_movie_terminal_proven_by_these_probes": False,
        "original_pixels_or_paths_in_output": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_manifest", type=Path)
    parser.add_argument("--private-frame-clock", type=Path)
    parser.add_argument("--private-frame-witness", type=Path)
    parser.add_argument("--private-cpu-executions", type=Path)
    parser.add_argument("--private-cpu-witness", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        result = audit_series(
            args.private_manifest, anchor_tsv=args.private_frame_clock,
            anchor_witness=args.private_frame_witness,
            cpu_tsv=args.private_cpu_executions,
            cpu_witness=args.private_cpu_witness)
        if args.out is not None:
            if args.out.is_symlink() or args.out.exists() or not args.out.parent.is_dir():
                raise ValueError("output must be a NEW private report file")
            args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        parser.exit(1, "PRIVATE_PPUMASK_SERIES_INCONCLUSIVE: " + str(exc) + "\n")
    print("PRIVATE_PPUMASK_SERIES_RASTER_REPEATABILITY_PASS")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
