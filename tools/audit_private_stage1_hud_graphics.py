#!/usr/bin/env python3
"""Private pixel-level comparison of Stage 1-1 HUD-sensitive CHR0/PPUMASK.

Only numerical aggregates are returned. Source ROM/FM2, private file paths,
original RGB/PAL arrays and copyrighted art MUST remain outside GitHub.
The optional legacy witness mode does NOT attest CPU-X restoration or prove
cross-session ROM identity hashes; its limitations are printed in the report.
"""
import argparse
import json
from pathlib import Path

WIDTH, HEIGHT, HUD_START = 256, 240, 196
PIXELS = WIDTH * HEIGHT
PPM_HEADER = b"P6\n256 240\n255\n"
CAPTURE_TYPES = {
    "original": ("private_ppumask_one_write_ab_v1", "original"),
    "ppumask": ("private_ppumask_one_write_ab_v1", "probe_bg_off"),
    "chr0": ("private_chr0_one_write_ab_v1", "chr_bank_0_two_probe"),
}


def _private_file(path, expected_size):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size != expected_size:
        raise ValueError("private screenshot missing, symlinked or malformed")
    return p.read_bytes()


def _folder(path):
    p = Path(path)
    if p.is_symlink() or not p.is_dir():
        raise ValueError("private directory missing or symlinked")
    return p


def _witness(root, target, kind):
    path = root / "COMPLETE.txt"
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 4096:
        raise ValueError("private original-session witness unavailable")
    fields = {}
    for line in path.read_text("ascii").splitlines():
        if "=" not in line:
            raise ValueError("invalid legacy FCEUX witness")
        key, value = line.split("=", 1)
        if key in fields:
            raise ValueError("duplicate witness metadata")
        fields[key] = value
    fmt, mode = CAPTURE_TYPES[kind]
    expected = {
        "format": fmt, "mode": mode, "frame": str(target),
        "last_observed_frame": str(target + 2), "frame_gaps": "0",
        "target_instruction_hits": "1", "fm2_readonly": "yes",
    }
    if kind == "chr0":
        expected.pop("target_instruction_hits")
        expected.update({
            "target_instruction_hits": "1",
            "accumulator_restored_before_e38a": "yes",
            "rom_identity_verified": "yes",
        })
    else:
        expected["source_rom_unchanged"] = "yes"
    if set(fields) != set(expected) | {"first_observed_frame"} or any(
            fields.get(key) != value for key, value in expected.items()):
        raise ValueError("legacy original FCEUX capture provenance inconsistent")
    if fields["first_observed_frame"] not in ("0", "1"):
        raise ValueError("original movie callback was attached late")
    # The CHR0 legacy witness mislabels X restoration as A restoration.
    # Deliberately do NOT imply independently verified CPU X restoration.
    return True


def _mask(a, b, width):
    if len(a) != len(b) or len(a) != PIXELS * width:
        raise ValueError("private image dimensions inconsistent")
    if width == 1:
        return bytes(x != y for x, y in zip(a, b))
    return bytes(a[i:i+width] != b[i:i+width]
                 for i in range(0, len(a), width))


def _capture(root, frame):
    basename = f"frame_{frame:06d}"
    raw = _private_file(root / (basename + ".ppm"),
                        len(PPM_HEADER) + PIXELS * 3)
    if not raw.startswith(PPM_HEADER):
        raise ValueError("invalid original P6 screenshot header")
    palette = _private_file(root / (basename + ".pal.bin"), PIXELS)
    return raw[len(PPM_HEADER):], palette


def _iou(a, b):
    if len(a) != len(b):
        raise ValueError("private mask dimensions differ")
    intersection = sum(x and y for x, y in zip(a, b))
    union = sum(x or y for x, y in zip(a, b))
    return {"intersection": intersection, "union": union,
            "iou": round(intersection / union, 6) if union else None}


def audit(manifest, *, acknowledge_legacy=False, hud_start=HUD_START):
    if not acknowledge_legacy:
        raise ValueError("legacy witness schema requires explicit acknowledgement")
    if type(hud_start) is not int or not 1 <= hud_start < HEIGHT:
        raise ValueError("invalid image-region boundary")
    path = Path(manifest)
    if path.is_symlink() or not path.is_file() or not 1 <= path.stat().st_size <= 65536:
        raise ValueError("private capture manifest invalid")
    cases = json.loads(path.read_text("utf8"))
    if not isinstance(cases, list) or not 2 <= len(cases) <= 8:
        raise ValueError("two to eight different capture frames are required")
    last = -1
    seen = set()
    reports = []
    masks = {"chr0": [], "ppumask": []}
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"frame", "original", "chr0", "ppumask"}:
            raise ValueError("private manifest entry schema mismatch")
        target = case["frame"]
        if type(target) is not int or target < 300 or target <= last:
            raise ValueError("private target frames must be unique and sorted")
        last = target
        roots = {}
        for kind in CAPTURE_TYPES:
            root = _folder(case[kind])
            canonical = root.resolve()
            if canonical in seen:
                raise ValueError("private capture directory reused across experiments")
            seen.add(canonical)
            roots[kind] = root
            _witness(root, target, kind)
        images = {}
        for frame in range(target - 1, target + 3):
            images[frame] = {kind: _capture(root, frame)
                             for kind, root in roots.items()}
        changed = {}
        for kind in ("chr0", "ppumask"):
            for frame in range(target - 1, target + 3):
                a_rgb, a_pal = images[frame]["original"]
                b_rgb, b_pal = images[frame][kind]
                rgb_mask = _mask(a_rgb, b_rgb, 3)
                pal_mask = _mask(a_pal, b_pal, 1)
                if rgb_mask != pal_mask:
                    raise ValueError("original RGB and indexed palette change masks diverged")
                if frame != target + 1 and any(pal_mask):
                    raise ValueError("diagnostic branch diverged outside next captured frame")
                if frame == target + 1:
                    changed[kind] = pal_mask
            if not any(changed[kind]):
                raise ValueError("expected visible one-frame response not observed")
            masks[kind].append(changed[kind])
        chr0, mask = changed["chr0"], changed["ppumask"]
        only0 = bytes(a and not b for a, b in zip(chr0, mask))
        onlym = bytes(b and not a for a, b in zip(chr0, mask))
        union = bytes(a or b for a, b in zip(chr0, mask))
        def rows(binary):
            return [y for y in range(HEIGHT)
                    if any(binary[y*WIDTH:(y+1)*WIDTH])]
        def top_count(binary):
            return sum(binary[:hud_start*WIDTH])
        if top_count(union):
            raise ValueError("expected diagnostic effects outside analyzed lower HUD region")
        counts = _iou(chr0, mask)
        reports.append({
            "target_frame": target,
            "first_affected_frame": target + 1,
            "chr0_changed_pixels": sum(chr0),
            "ppumask_changed_pixels": sum(mask),
            "overlapping_changed_pixels": counts["intersection"],
            "chr0_only_changed_pixels": sum(only0),
            "ppumask_only_changed_pixels": sum(onlym),
            "chr0_ppumask_change_mask_iou": counts["iou"],
            "chr0_affected_rows": rows(chr0),
            "ppumask_affected_rows": rows(mask),
            "chr0_only_affected_rows": rows(only0),
            "chr0_rows_not_affected_by_ppumask":
                sorted(set(rows(chr0)) - set(rows(mask))),
            "upper_image_pixels_changed": top_count(union),
            "rgb_palette_masks_identical": True,
        })
    temporal = {kind: _iou(masks[kind][0], masks[kind][1])
                for kind in ("chr0", "ppumask")}
    return {
        "schema": "vpd_stage159_chr0_ppumask_spatial_mask_comparison_v1",
        "classification": "private original CHR0/PPUMASK counterfactual, not original scene rendering proof",
        "framebuffer_dimensions": [WIDTH, HEIGHT],
        "analysis_hud_region_start_y": hud_start,
        "hud_boundary_is_manual_image_classification_not_ppu_raster_timing": True,
        "frames_compared": len(reports),
        "per_frame": reports,
        "cross_frame_spatial_iou_first_two_cases": temporal,
        "only_lower_hud_region_responded_in_tested_frames": True,
        "legacy_chr0_witness_mislabels_cpu_x_restoration_as_a": True,
        "cpu_x_restoration_independently_attested_by_legacy_witness": False,
        "rom_hash_cross_checked_between_legacy_capture_schemas": False,
        "ppu_scanline_origin_proven": False,
        "original_car_camera_speed_proven": False,
        "switch_hud_implementation_proven": False,
        "source_pixels_or_private_paths_in_output": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_manifest", type=Path)
    parser.add_argument("--acknowledge-legacy-witness", action="store_true")
    parser.add_argument("--hud-start-y", type=int, default=HUD_START)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.private_manifest,
                       acknowledge_legacy=args.acknowledge_legacy_witness,
                       hud_start=args.hud_start_y)
        if args.output is not None:
            if args.output.is_symlink() or args.output.exists() or not args.output.parent.is_dir():
                raise ValueError("output must be a NEW private report file")
            args.output.write_text(json.dumps(result, indent=2) + "\n", "utf8")
    except (ValueError, UnicodeError, OSError, TypeError) as e:
        parser.exit(1, "PRIVATE_STAGE159_HUD_AUDIT_INCONCLUSIVE: " + str(e) + "\n")
    print("PRIVATE_STAGE159_HUD_GRAPHIC_RESPONSE_PASS")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
