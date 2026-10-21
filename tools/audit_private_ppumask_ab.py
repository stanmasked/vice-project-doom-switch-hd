#!/usr/bin/env python3
"""Compare PRIVATE FCEUX screenshots before/after one PPUMASK diagnostic write.

The ROM and FM2 remain unchanged, but CPU A is briefly perturbed in the
intervention branch. Pixel data, palette arrays and private paths never
appear in output. A changed screenshot row is NOT proof of the CPU write's
exact raster scanline or of unmodified-game scrolling.
"""
import argparse
import json
from pathlib import Path

WIDTH, HEIGHT = 256, 240
PPM_HEADER = b'P6\n256 240\n255\n'
PIXELS = WIDTH * HEIGHT
EXPECTED_SIZE = len(PPM_HEADER) + PIXELS * 3
PALETTE_SIZE = PIXELS


def _directory(path):
    p = Path(path)
    if p.is_symlink() or not p.is_dir():
        raise ValueError('private capture directory missing or symlinked')
    return p


def _read(path, maximum):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= maximum:
        raise ValueError('private capture file missing, symlinked or oversized')
    return path.read_bytes()


def _witness(directory, mode, target):
    raw = _read(directory / 'COMPLETE.txt', 4096).decode('ascii')
    fields = {}
    for line in raw.splitlines():
        if '=' not in line:
            raise ValueError('malformed private witness')
        key, val = line.split('=', 1)
        if key in fields:
            raise ValueError('duplicate private witness field')
        fields[key] = val
    expected = {
        'format': 'private_ppumask_one_write_ab_v1',
        'mode': mode,
        'frame': str(target),
        'last_observed_frame': str(target + 2),
        'frame_gaps': '0',
        'target_instruction_hits': '1',
        'source_rom_unchanged': 'yes',
        'fm2_readonly': 'yes',
    }
    normal = set(expected) | {'first_observed_frame'}
    if set(fields) not in (normal, normal | {'accumulator_restored_before_rts'}):
        raise ValueError('incomplete or unexpected private A/B witness schema')
    restored = fields.get('accumulator_restored_before_rts')
    if restored is not None and restored != (
            'yes' if mode == 'probe_bg_off' else 'not_needed'):
        raise ValueError('private CPU accumulator restore witness invalid')
    if any(fields[key] != val for key, val in expected.items()):
        raise ValueError('private A/B capture identity or completeness mismatch')
    if fields['first_observed_frame'] not in ('0', '1'):
        raise ValueError('private playback callback was attached late')
    return restored is not None


def _pixel_differences(first, second, channels):
    if len(first) != len(second) or len(first) != PIXELS * channels:
        raise ValueError('invalid private image size')
    counts = [0] * HEIGHT
    changed = 0
    for y in range(HEIGHT):
        base = y * WIDTH * channels
        for x in range(WIDTH):
            i = base + x * channels
            if first[i:i + channels] != second[i:i + channels]:
                changed += 1
                counts[y] += 1
    rows = [y for y, amount in enumerate(counts) if amount]
    return {'pixels': changed, 'row_count': len(rows),
            'first_row': rows[0] if rows else None,
            'last_row': rows[-1] if rows else None}


def audit(original_dir, diagnostic_dir, *, target_frame):
    if type(target_frame) is not int or not 300 <= target_frame <= 100000:
        raise ValueError('invalid target frame')
    orig = _directory(original_dir)
    diagnostic = _directory(diagnostic_dir)
    if orig.resolve() == diagnostic.resolve():
        raise ValueError('original and intervention captures cannot be the same directory')
    original_restoration_witness = _witness(orig, 'original', target_frame)
    diagnostic_restoration_witness = _witness(diagnostic, 'probe_bg_off', target_frame)
    rows = []
    altered_frames = []
    union_min, union_max = None, None
    for frame in range(target_frame - 1, target_frame + 3):
        name = f'frame_{frame:06d}'
        original_rgb = _read(orig / (name + '.ppm'), EXPECTED_SIZE)
        modified_rgb = _read(diagnostic / (name + '.ppm'), EXPECTED_SIZE)
        if (len(original_rgb) != EXPECTED_SIZE or len(modified_rgb) != EXPECTED_SIZE
            or not original_rgb.startswith(PPM_HEADER)
            or not modified_rgb.startswith(PPM_HEADER)):
            raise ValueError('private P6 screenshot invalid')
        original_pal = _read(orig / (name + '.pal.bin'), PALETTE_SIZE)
        modified_pal = _read(diagnostic / (name + '.pal.bin'), PALETTE_SIZE)
        if len(original_pal) != PALETTE_SIZE or len(modified_pal) != PALETTE_SIZE:
            raise ValueError('private NES palette screenshot invalid')
        rgb = _pixel_differences(original_rgb[len(PPM_HEADER):],
                                 modified_rgb[len(PPM_HEADER):], 3)
        pal = _pixel_differences(original_pal, modified_pal, 1)
        if frame == target_frame - 1 and (rgb['pixels'] or pal['pixels']):
            raise ValueError('captures diverged before the intended register intervention')
        if rgb['pixels'] or pal['pixels']:
            altered_frames.append(frame)
        if rgb['row_count']:
            union_min = (rgb['first_row'] if union_min is None
                         else min(union_min, rgb['first_row']))
            union_max = (rgb['last_row'] if union_max is None
                         else max(union_max, rgb['last_row']))
        rows.append({'frame': frame, 'rgb_changed': rgb,
                     'palette_changed': pal})
    return {
        'schema': 'vpd_private_ppumask_ab_raster_diff_v1',
        'classification': 'controlled emulator intervention; NOT unmodified-game scroll proof',
        'target_original_cpu_instruction': '$E38E',
        'original_ppumask_value': '$0E',
        'diagnostic_ppumask_value': '$06',
        'target_cpu_frame': target_frame,
        'first_changed_capture_frame': altered_frames[0] if altered_frames else None,
        'changed_capture_frames': altered_frames,
        'rgb_affected_row_min': union_min,
        'rgb_affected_row_max': union_max,
        'pixel_differences': rows,
        'pre_intervention_images_match': True,
        'rom_and_fm2_untouched_in_both_sessions': True,
        'diagnostic_cpu_register_modified_once': True,
        'diagnostic_accumulator_restored_before_rts_verified':
            diagnostic_restoration_witness,
        'baseline_explicit_accumulator_witness': original_restoration_witness,
        'same_frame_render_latency_proven': False,
        'exact_ppu_scanline_of_cpu_write_proven': False,
        'actual_stage_camera_speed_proven': False,
        'gameplay_behavior_equivalent_after_intervention': False,
        'original_pixels_in_report': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_unmodified_capture', type=Path)
    parser.add_argument('private_intervention_capture', type=Path)
    parser.add_argument('--target-frame', type=int, required=True)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.private_unmodified_capture,
                       args.private_intervention_capture,
                       target_frame=args.target_frame)
        if args.out is not None:
            if args.out.is_symlink() or args.out.exists() or not args.out.parent.is_dir():
                raise ValueError('private report must be written to a NEW regular file')
            args.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    except (OSError, ValueError, UnicodeError) as error:
        parser.exit(1, 'PRIVATE_PPUMASK_AB_INCONCLUSIVE: ' + str(error) + '\n')
    print('PRIVATE_PPUMASK_AB_RASTER_DIFF_PASS')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
