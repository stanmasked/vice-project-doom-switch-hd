#!/usr/bin/env python3
"""Stage92: cross-snapshot screen consistency, not game camera reconstruction.

All inputs must belong to a completely verified FCEUX capture session.
Only aggregate numbers are emitted; never publish private captured data.
"""
import argparse
import json
from pathlib import Path

from audit_ppu_background_readiness import (
    TOTAL_CELLS, CELL, WIDTH, HEIGHT, analyze_verified as readiness_audit,
)
from audit_ppu_reference_frames import analyze_verified as inventory_audit
from compare_rendered_frame import PIXELS, load_reference


PAIR_CLASSES = (
    'fully_known_identical',
    'fully_known_changed',
    'partially_unknown',
    'unassessed_missing_reference',
)


def compare_saved_screen_cells(before, after):
    """Compare identical screen coordinates, never claimed world-tile identity.

    If either reference has an unavailable (254) palette index in the cell,
    exclude the complete cell rather than comparing an incomplete subset.
    """
    if len(before) != PIXELS or len(after) != PIXELS:
        raise ValueError('Both references must be complete 256x240 palette planes')
    if any(p > 63 and p != 254 for p in before + after):
        raise ValueError('A palette plane contains an invalid index')
    counts = dict.fromkeys(PAIR_CLASSES, 0)
    for y in range(0, HEIGHT, CELL):
        for x in range(0, WIDTH, CELL):
            indices = (row * WIDTH + col
                       for row in range(y, y + CELL)
                       for col in range(x, x + CELL))
            identical = True
            unknown = False
            for i in indices:
                a, b = before[i], after[i]
                if a == 254 or b == 254:
                    unknown = True
                elif a != b:
                    identical = False
            if unknown:
                counts['partially_unknown'] += 1
            elif identical:
                counts['fully_known_identical'] += 1
            else:
                counts['fully_known_changed'] += 1
    if sum(counts.values()) != TOTAL_CELLS:
        raise ValueError('Screen-cell accounting error')
    return counts


def no_reference_pair():
    return {key: (TOTAL_CELLS if key == 'unassessed_missing_reference'
                  else 0) for key in PAIR_CLASSES}


def analyze_verified(session_meta, *, require_cycle=False,
                     require_screen_pair=False):
    """Bind Stage91 static evidence and Stage88 memory deltas to exact pairs."""
    session_meta = Path(session_meta)
    # Stage91 verifies the complete session, including event prefixes and all
    # snapshot / screen checksums, before viewing any actual screen data.
    ready = readiness_audit(session_meta, require_cycle=require_cycle)
    # Stage88 independently re-verifies the same complete session before
    # computing raw memory changes between consecutive captured snapshots.
    inventory = inventory_audit(session_meta, require_cycle=require_cycle)
    if ready['session_id'] != inventory['verified_session_id']:
        raise ValueError('Conflicting verified session identifiers')
    if ready['frames_captured'] != inventory['frames_captured']:
        raise ValueError('Conflicting verified snapshot counts')
    frames = ready['frames']
    snaps = inventory['snapshots']
    deltas = inventory['changes_between_snapshots']
    if len(deltas) != max(0, len(frames) - 1):
        raise ValueError('Unexpected count of verified memory comparisons')
    if [f['frame'] for f in frames] != [s['frame'] for s in snaps]:
        raise ValueError('Background and inventory snapshot ordering disagree')
    pairs = []
    with_screen = 0
    for index, delta in enumerate(deltas, 1):
        before, after = frames[index - 1], frames[index]
        first, last = before['frame'], after['frame']
        if delta['from_frame'] != first or delta['to_frame'] != last:
            raise ValueError('Verified memory transition label mismatch')
        before_screen = before['reference_status'] == 'verified_saved_screen'
        after_screen = after['reference_status'] == 'verified_saved_screen'
        status = (
            'both_verified' if before_screen and after_screen else
            'earlier_missing' if not before_screen and after_screen else
            'later_missing' if before_screen and not after_screen else
            'both_missing'
        )
        if before_screen and after_screen:
            with_screen += 1
            a_prefix = session_meta.parent / f'frame_{first:06d}'
            b_prefix = session_meta.parent / f'frame_{last:06d}'
            _a_rgb, a = load_reference(a_prefix)
            _b_rgb, b = load_reference(b_prefix)
            counts = compare_saved_screen_cells(a, b)
        else:
            counts = no_reference_pair()
        event_window = after['event_window']
        chr_writes = event_window['observed_chr_data_writes']
        scroll_writes = event_window['observed_ppuscroll_writes']
        addr_writes = event_window['observed_ppuaddr_writes']
        pairs.append({
            'from_snapshot_frame': first,
            'to_snapshot_frame': last,
            'frame_label_distance': last - first,
            'unobserved_frame_labels_between': last - first - 1,
            'screen_reference_pair_status': status,
            'screen_cells_per_snapshot': TOTAL_CELLS,
            'evaluated_screen_cells': TOTAL_CELLS if status == 'both_verified' else 0,
            'screen_cell_counts': counts,
            'same_coordinate_screen_stability_proven_for_fully_known_cells':
                status == 'both_verified',
            'background_or_world_tile_stability_proven': False,
            'stage91_static_candidate_counts': {
                'earlier_exact_candidate_cells':
                    before['static_exact_match_candidate_cells'],
                'later_exact_candidate_cells':
                    after['static_exact_match_candidate_cells'],
                'spatial_correspondence_between_candidates_proven': False,
            },
            'intervening_verified_cpu_event_window': {
                'observed_register_events':
                    event_window['observed_cpu_register_events'],
                'chr_register_data_writes': chr_writes,
                'ppuscroll_writes': scroll_writes,
                'complete_observed_ppuscroll_pairs':
                    event_window['observed_complete_scroll_pairs'],
                'ppuaddr_writes': addr_writes,
                'chr_or_scroll_or_ppuaddr_activity_observed':
                    bool(chr_writes or scroll_writes or addr_writes),
                'physical_scanline_of_writes_proven': False,
            },
            'verified_snapshot_memory_deltas': {
                'ppu_changed_bytes': delta['ppu_changed_bytes'],
                'chr_1k_changed_bytes_total':
                    sum(delta['chr_1k_changed_bytes']),
                'nametable_tile_cells_changed_total':
                    sum(delta['nametable_tile_cells_changed']),
                'nametable_attribute_bytes_changed_total':
                    sum(delta['nametable_attribute_bytes_changed']),
                'palette_memory_bytes_changed':
                    delta['palette_memory_bytes_changed'],
                'memory_changes_explain_rendered_pixels': False,
            },
            'camera_offset_inferred': False,
            'level_geometry_reconstruction_ready_cells': 0,
        })
    if require_screen_pair and with_screen == 0:
        raise ValueError('No consecutive saved snapshot pair has two verified screens')
    totals = {key: sum(pair['screen_cell_counts'][key] for pair in pairs)
              for key in PAIR_CLASSES}
    if sum(totals.values()) != TOTAL_CELLS * len(pairs):
        raise ValueError('Incomplete cross-snapshot cell accounting')
    return {
        'format': 'vpd_verified_cross_snapshot_consistency_v1',
        'session_verified': True,
        'session_id': ready['session_id'],
        'frames_captured': ready['frames_captured'],
        'snapshot_pairs': len(pairs),
        'screen_reference_pairs_compared': with_screen,
        'cpu_cycle_trace_verified': ready['cpu_cycle_trace_verified'],
        'aggregate_screen_cell_counts': totals,
        'level_geometry_reconstruction_ready_cells': 0,
        'pairs': pairs,
        'interpretation': {
            'measurement': 'Same-screen-coordinate palette-index consistency between saved snapshots',
            'intermediate_frame_content_known': False,
            'observed_event_prefixes_verified': True,
            'cpu_events_aligned_to_ppu_raster': False,
            'ppu_chr_mapping_at_scanlines_proven': False,
            'sprite_background_separation_proven': False,
            'camera_motion_reconstructed': False,
            'original_game_identity_authenticated': False,
            'first_level_geometry_proven': False,
            'raw_indices_images_or_bank_values_exported': False,
        },
        'next_required_observations': [
            'Independent first-level capture identity and rendering provenance',
            'Scanline-accurate CHR/scroll visibility rather than CPU callbacks alone',
            'Sprite/effect separation before background temporal inference',
            'Verified camera displacement and world-space tile continuity',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session_meta', type=Path)
    parser.add_argument('--require-cycle', action='store_true')
    parser.add_argument('--require-screen-pair', action='store_true')
    parser.add_argument('--out', type=Path,
                        help='Local private numeric summary, never original captures')
    args = parser.parse_args()
    result = analyze_verified(
        args.session_meta, require_cycle=args.require_cycle,
        require_screen_pair=args.require_screen_pair)
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding='utf8')
    print(text, end='')


if __name__ == '__main__':
    main()
