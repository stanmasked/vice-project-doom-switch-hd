#!/usr/bin/env python3
"""Stage93: registered CPU-event ordering versus verified saved screen pairs.

Labels are FCEUX callback frames, NOT measured physical PPU scanlines.
Aggregate event families only; no register values, pixels or camera offsets.
"""
import argparse
import json
from pathlib import Path

from audit_ppu_cross_snapshot_consistency import analyze_verified as screen_pairs
from audit_ppu_event_provenance import audit_verified as event_windows
from verify_ppu_capture_session import read_frame_events


FAMILIES = ('chr_context', 'scroll_address', 'display_control',
            'ppu_data', 'status_latch', 'other')
VISIBLE_RELATED = FAMILIES[:4]


def event_family(address, selector):
    """Classify the observed callback; selector tracks MMC3 R0-R7 selection.

    An even $8000-$9FFF write is conservatively a CHR *context* event:
    it can select a PRG register or update the inversion bit. It does not
    establish that rendered CHR changed.
    """
    if 0x8000 <= address <= 0x9FFF:
        if address % 2 == 0:
            return 'chr_context'
        return ('chr_context'
                if selector is None or selector <= 5 else 'other')
    if 0xA000 <= address <= 0xBFFF and address % 2 == 0:
        return 'display_control'  # MMC3 nametable mirroring control
    if 0x2000 <= address <= 0x3FFF:
        port = (address - 0x2000) % 8
        return {
            0: 'display_control', 1: 'display_control',
            2: 'status_latch', 5: 'scroll_address',
            6: 'scroll_address', 7: 'ppu_data',
        }.get(port, 'other')
    return 'other'


def summarize_callback_window(events, *, starting_selector=None,
                              previous_snapshot_frame=None,
                              ending_snapshot_frame=None):
    """Summarize event order without returning raw selector or register values.

    The caller must verify the whole session and committed event prefixes
    before using this function on private captures.
    """
    if starting_selector is not None and starting_selector not in range(8):
        raise ValueError('Invalid MMC3 starting selector')
    selector = starting_selector
    counts = {name: 0 for name in FAMILIES}
    order = []
    labels = set()
    before_or_at_prior = 0
    for frame, address, value in events:
        if (ending_snapshot_frame is not None
                and frame > ending_snapshot_frame):
            raise ValueError('Event label exceeds committed snapshot')
        family = event_family(address, selector)
        counts[family] += 1
        labels.add(frame)
        if previous_snapshot_frame is not None and frame <= previous_snapshot_frame:
            before_or_at_prior += 1
        if family in VISIBLE_RELATED and (not order or order[-1] != family):
            order.append(family)
        if 0x8000 <= address <= 0x9FFF and address % 2 == 0:
            selector = value & 7
    distinct = len(set(order))
    if not order:
        shape = 'no_selected_background_related_callbacks'
    elif distinct == 1:
        shape = 'single_callback_family'
    elif len(order) == distinct:
        shape = 'multiple_families_without_return'
    else:
        shape = 'interleaved_callback_families'
    return {
        'registered_callbacks': len(events),
        'counts_by_family': counts,
        'background_related_callback_count':
            sum(counts[name] for name in VISIBLE_RELATED),
        'distinct_registered_callback_frame_labels': len(labels),
        'events_labeled_at_or_before_previous_snapshot':
            before_or_at_prior,
        'collapsed_background_family_transitions': max(0, len(order) - 1),
        'ordered_family_signature': shape,
        'cpu_callback_sequence_known': True,
        'ppu_visible_order_known': False,
    }, selector


def screen_activity_relation(pair, summary):
    """Observed correlation only; no causality, camera, or raster inference."""
    if pair['screen_reference_pair_status'] != 'both_verified':
        return 'screen_reference_pair_unavailable'
    cells = pair['screen_cell_counts']
    known = cells['fully_known_identical'] + cells['fully_known_changed']
    if known == 0:
        return 'no_fully_observed_comparable_screen_cells'
    activity = summary['background_related_callback_count'] > 0
    changed = cells['fully_known_changed'] > 0
    if changed and activity:
        return 'screen_change_and_registered_activity_cooccur'
    if changed:
        return 'screen_change_without_selected_registered_activity'
    if activity:
        return 'no_known_screen_change_despite_registered_activity'
    return 'no_known_screen_change_and_no_selected_registered_activity'


def analyze_verified(session_meta, *, require_cycle=False,
                     require_screen_pair=False):
    """Fail closed on the underlying snapshot, register, screen and TSV checks."""
    session_meta = Path(session_meta)
    screen = screen_pairs(session_meta, require_cycle=require_cycle,
                          require_screen_pair=require_screen_pair)
    provenance = event_windows(session_meta, require_cycle=require_cycle)
    if screen['session_id'] != provenance['session_id']:
        raise ValueError('Verified session identifiers disagree')
    windows = provenance['windows']
    if screen['frames_captured'] != len(windows):
        raise ValueError('Snapshot window count inconsistent')
    if len(screen['pairs']) != max(0, len(windows) - 1):
        raise ValueError('Snapshot pair count inconsistent')
    # Both prior analyses have independently verified the complete session.
    events = read_frame_events(session_meta.parent / 'mmc3_video_writes.tsv')
    output_pairs = []
    selector = None
    cursor = 0
    for index, window in enumerate(windows):
        start, stop = (window['event_start_index'],
                       window['event_end_index_exclusive'])
        if start != cursor or stop < start or stop > len(events):
            raise ValueError('Noncontiguous verified event checkpoints')
        current = window['to_snapshot_frame']
        previous = window['from_snapshot_frame']
        summary, selector = summarize_callback_window(
            events[start:stop], starting_selector=selector,
            previous_snapshot_frame=previous,
            ending_snapshot_frame=current)
        if summary['registered_callbacks'] != window['observed_register_events']:
            raise ValueError('Event count differs from verified provenance')
        # Stage90 has already independently replayed the same selected
        # MMC3 + PPU callbacks; cross-check their overlapping categories.
        counters = window['event_counts']
        if summary['counts_by_family']['scroll_address'] != (
                counters['ppuscroll_writes'] + counters['ppuaddr_writes']):
            raise ValueError('Scroll/address callback disagreement')
        if summary['counts_by_family']['status_latch'] != counters[
                'ppustatus_read_markers']:
            raise ValueError('Latch callback disagreement')
        cursor = stop
        if index == 0:
            continue  # No earlier saved screen exists for the first window.
        pair = screen['pairs'][index - 1]
        if (pair['from_snapshot_frame'] != previous
                or pair['to_snapshot_frame'] != current):
            raise ValueError('Screen pair is not the verified event window')
        relation = screen_activity_relation(pair, summary)
        output_pairs.append({
            'from_snapshot_frame': previous,
            'to_snapshot_frame': current,
            'callback_frame_label_distance': current - previous,
            'intervening_frames_without_saved_screen_snapshot':
                current - previous - 1,
            'screen_reference_pair_status':
                pair['screen_reference_pair_status'],
            'known_identical_screen_cells':
                pair['screen_cell_counts']['fully_known_identical'],
            'known_changed_screen_cells':
                pair['screen_cell_counts']['fully_known_changed'],
            'partially_unknown_screen_cells':
                pair['screen_cell_counts']['partially_unknown'],
            'callback_window': summary,
            'screen_and_callback_relation': relation,
            'mmc3_selector_seen_since_session_start':
                window['observed_register_state_at_checkpoint'][
                    'chr_selector_observed'],
            'all_six_chr_registers_seen_since_session_start':
                window['observed_register_state_at_checkpoint'][
                    'all_six_chr_registers_observed_since_start'],
            'scroll_latch_synchronized_by_observed_status_read':
                window['observed_register_state_at_checkpoint'][
                    'ppuscroll_write_toggle_synchronized'],
            'incomplete_scroll_pair_at_checkpoint':
                window['observed_register_state_at_checkpoint'][
                    'pending_first_ppuscroll_write'],
            'chr_or_scroll_visible_scanlines_proven': False,
            'screen_change_attributable_to_callback_family': False,
            'camera_displacement_inferred': False,
            'background_or_sprite_causality_proven': False,
            'level_geometry_reconstruction_ready_cells': 0,
        })
    if cursor > len(events):
        raise ValueError('Invalid final event checkpoint')
    return {
        'format': 'vpd_verified_ppu_temporal_evidence_v1',
        'session_verified': True,
        'session_id': screen['session_id'],
        'snapshot_pairs': len(output_pairs),
        'screen_reference_pairs_compared':
            screen['screen_reference_pairs_compared'],
        'verified_cpu_cycle_trace_available':
            screen['cpu_cycle_trace_verified'],
        'events_after_last_snapshot': provenance['events_after_last_snapshot'],
        'pairs': output_pairs,
        'interpretation': {
            'cpu_callbacks_in_committed_event_prefix_order': True,
            'callback_frame_labels_are_physical_frame_boundaries': False,
            'cpu_cycles_are_ppu_scanlines': False,
            'ppu_raster_bank_mapping_proven': False,
            'visible_scroll_timeline_proven': False,
            'display_changes_causally_attributed': False,
            'background_vs_sprite_separation_proven': False,
            'camera_trajectory_proven': False,
            'original_first_level_identity_proven': False,
            'original_level_geometry_reconstructed': False,
            'raw_pixel_or_register_values_exported': False,
        },
        'next_evidence_required': [
            'Capture independent scanline-aligned PPU-visible CHR/scroll traces',
            'Authenticate original first-level sequence privately',
            'Separate sprites/effects and PPU memory writes from background',
            'Verify camera/world coordinate continuity across full rendered frames',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session_meta', type=Path)
    parser.add_argument('--require-cycle', action='store_true')
    parser.add_argument('--require-screen-pair', action='store_true')
    parser.add_argument('--out', type=Path,
                        help='Private local numeric report; do not commit it')
    args = parser.parse_args()
    result = analyze_verified(
        args.session_meta, require_cycle=args.require_cycle,
        require_screen_pair=args.require_screen_pair)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding='utf8')
    print(encoded, end='')


if __name__ == '__main__':
    main()
