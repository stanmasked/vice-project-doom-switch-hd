#!/usr/bin/env python3
"""Analyze owner-PRIVATE CHR-bank A/B screen captures without leaking pixels.

A no-difference result only means this particular read-only FM2 window's
captured RGB/palette images did not respond to one diagnostic MMC3 value.
It cannot prove the bank is unused, that CHR memory is identical, or that
all raster states are unchanged.
"""
import argparse
import json
from pathlib import Path

SIZE_X, SIZE_Y = 256, 240
PIXELS = SIZE_X * SIZE_Y
HEADER = b"P6\n256 240\n255\n"
RGB_BYTES = len(HEADER) + 3 * PIXELS
PAL_BYTES = PIXELS
BANK_SPECS = {
    0: {
        "format": "private_chr_bank0_one_write_ab_v1",
        "probe_mode": "probe_chr0_two",
        "restore_key": "cpu_x_restored_before_e383",
        "pc": "$E380", "restoration_pc": "$E383",
        "original_value": "$00", "probe_value": "$02",
    },
    1: {
        "format": "private_chr_bank1_one_write_ab_v1",
        "probe_mode": "probe_chr1_zero",
        "restore_key": "accumulator_restored_before_e38a",
        "pc": "$E387", "restoration_pc": "$E38A",
        "original_value": "$02", "probe_value": "$00",
    },
}
COMMON_WITNESS_KEYS = {
    "format", "mode", "target_frame", "first_observed_frame",
    "last_observed_frame", "frame_gaps", "writer_pc_hits",
    "next_instruction_hits", "rom_payload_md5", "fm2_readonly",
}


def _dir(path):
    p = Path(path)
    if p.is_symlink() or not p.is_dir():
        raise ValueError("private capture directory missing or symlinked")
    return p


def _read(path, size):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
        raise ValueError("missing, symlinked or malformed private capture")
    return path.read_bytes()


def _witness(path, target, mode, bank):
    path = _dir(path)
    file = path / "COMPLETE.txt"
    if file.is_symlink() or not file.is_file() or not 1 <= file.stat().st_size <= 4096:
        raise ValueError("private capture completion witness missing")
    fields = {}
    for line in file.read_text("ascii").splitlines():
        if "=" not in line:
            raise ValueError("invalid witness metadata")
        key, value = line.split("=", 1)
        if key in fields:
            raise ValueError("duplicate witness metadata")
        fields[key] = value
    spec = BANK_SPECS[bank]
    if set(fields) != COMMON_WITNESS_KEYS | {spec["restore_key"]}:
        raise ValueError("private CHR witness schema mismatch")
    expected = {
        "format": spec["format"],
        "mode": mode,
        "target_frame": str(target),
        "last_observed_frame": str(target + 2),
        "frame_gaps": "0",
        "writer_pc_hits": "1",
        "next_instruction_hits": "1",
        spec["restore_key"]:
            "yes" if mode == spec["probe_mode"] else "not_needed",
        "fm2_readonly": "yes",
    }
    if any(fields[k] != v for k, v in expected.items()):
        raise ValueError("private CHR intervention or completeness witness invalid")
    if fields["first_observed_frame"] not in ("0", "1"):
        raise ValueError("movie callback attached after original movie start")
    identity = fields["rom_payload_md5"].lower()
    if len(identity) != 32 or any(c not in "0123456789abcdef" for c in identity):
        raise ValueError("private ROM payload hash malformed")
    return identity


def _pixel_masks(original, probe, channels):
    if len(original) != PIXELS * channels or len(probe) != PIXELS * channels:
        raise ValueError("unexpected frame dimensions")
    counts = [0] * SIZE_Y
    for y in range(SIZE_Y):
        offset = y * SIZE_X * channels
        for x in range(SIZE_X):
            a = offset + x * channels
            if original[a:a + channels] != probe[a:a + channels]:
                counts[y] += 1
    return counts


def audit(control_dir, diagnostic_dir, *, frame, bank_register=1):
    if type(frame) is not int or frame < 300 or frame > 100000:
        raise ValueError("invalid original movie target frame")
    if type(bank_register) is not int or bank_register not in BANK_SPECS:
        raise ValueError("unsupported MMC3 CHR register")
    spec = BANK_SPECS[bank_register]
    control = _dir(control_dir)
    diagnostic = _dir(diagnostic_dir)
    if control.resolve() == diagnostic.resolve():
        raise ValueError("control and diagnostic folders cannot be identical")
    original_id = _witness(control, frame, "original", bank_register)
    probe_id = _witness(diagnostic, frame, spec["probe_mode"], bank_register)
    if original_id != probe_id:
        raise ValueError("private CHR captures came from different original ROMs")
    results = []
    any_rgb_change = False
    any_palette_change = False
    for f in range(frame - 1, frame + 3):
        basename = f"frame_{f:06d}"
        orig_rgb = _read(control / (basename + ".ppm"), RGB_BYTES)
        probe_rgb = _read(diagnostic / (basename + ".ppm"), RGB_BYTES)
        if not orig_rgb.startswith(HEADER) or not probe_rgb.startswith(HEADER):
            raise ValueError("invalid FCEUX RGB P6 image header")
        orig_pal = _read(control / (basename + ".pal.bin"), PAL_BYTES)
        probe_pal = _read(diagnostic / (basename + ".pal.bin"), PAL_BYTES)
        rgb_rows = _pixel_masks(orig_rgb[len(HEADER):],
                                probe_rgb[len(HEADER):], 3)
        palette_rows = _pixel_masks(orig_pal, probe_pal, 1)
        rgb_changed = sum(rgb_rows)
        palette_changed = sum(palette_rows)
        if f == frame - 1 and (rgb_changed or palette_changed):
            raise ValueError("control and probe diverged before the CHR intervention")
        rows = [i for i in range(SIZE_Y) if rgb_rows[i] or palette_rows[i]]
        any_rgb_change |= rgb_changed > 0
        any_palette_change |= palette_changed > 0
        results.append({
            "frame": f, "rgb_pixels_different": rgb_changed,
            "palette_indices_different": palette_changed,
            "affected_row_indices": rows,
            "rgb_palette_row_counts_match": rgb_rows == palette_rows,
        })
    return {
        "schema": "vpd_private_chr_register_counterfactual_v1",
        "classification": "private single-write CHR bank counterfactual; no original assets",
        "cpu_write_pc": spec["pc"],
        "mmc3_chr_register_number": bank_register,
        "original_mmc3_register_value": spec["original_value"],
        "counterfactual_mmc3_register_value": spec["probe_value"],
        "cpu_register_restored_at": spec["restoration_pc"],
        "original_frame_target": frame,
        "frames": results,
        "visible_rgb_difference_observed": any_rgb_change,
        "visible_palette_difference_observed": any_palette_change,
        "all_captured_frames_identical":
            not any_rgb_change and not any_palette_change,
        "source_rom_identity_compared_privately": True,
        "rom_or_fm2_bytes_modified": False,
        "fm2_movie_bytes_independently_hashed_by_auditor": False,
        "ppu_chr_mapping_proven_identical": False,
        "effect_on_other_original_frames_proven_absent": False,
        "ppu_scanline_effect_verified": False,
        "original_road_camera_speed_proven": False,
        "original_pixels_or_private_paths_in_report": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_unmodified_dir", type=Path)
    parser.add_argument("private_chr_probe_dir", type=Path)
    parser.add_argument("--frame", type=int, required=True)
    parser.add_argument("--chr-register", type=int, choices=(0, 1), default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.private_unmodified_dir, args.private_chr_probe_dir,
                       frame=args.frame, bank_register=args.chr_register)
        if args.output is not None:
            out = args.output
            if out.is_symlink() or out.exists() or not out.parent.is_dir():
                raise ValueError("private report output must be a NEW file")
            out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    except (ValueError, UnicodeError, OSError) as exc:
        parser.exit(1, "PRIVATE_CHR_AB_INCONCLUSIVE: " + str(exc) + "\n")
    print("PRIVATE_CHR_BANK_AB_AUDIT_PASS")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
