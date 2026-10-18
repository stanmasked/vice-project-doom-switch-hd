#!/usr/bin/env python3
"""Stage94: CPU-cycle bracketing around verified FCEUX snapshot clock samples.

Samples from registerafter callbacks are NOT physical PPU VBlank boundaries.
Do not convert CPU-cycle differences to scanline indices or camera motion.
"""
import argparse
import json
from pathlib import Path

from audit_ppu_temporal_evidence import analyze_verified as temporal_audit
from audit_ppu_temporal_evidence import event_family, FAMILIES
from verify_ppu_capture_session import (
    check_cycle_events, metadata, read_frame_events, verify,
)

REGIONS = (
    'at_previous_sample_clock',
    'strictly_between_sample_clocks',
    'at_current_sample_clock',
    'indistinguishable_equal_sample_clocks',
    'unanchored',
)


def bracket(cycle, previous, current):
    """Mutually exclusive CPU timestamp groups; NEVER a raster-time class."""
    if previous is None or current is None:
        return 'unanchored'
    if previous > current:
        raise ValueError('Decreasing verified snapshot CPU clock samples')
    if cycle is None:
        raise ValueError('Missing event CPU cycle with sampled snapshot clocks')
    if cycle < previous or cycle > current:
        raise ValueError('Committed event timestamp outside snapshot clock bracket')
    if previous == current:
        return 'indistinguishable_equal_sample_clocks'
    if cycle == previous:
        return 'at_previous_sample_clock'
    if cycle == current:
        return 'at_current_sample_clock'
    return 'strictly_between_sample_clocks'


def summarize_bracket(events, cycles, *, starting_selector=None,
                      previous_clock=None, current_clock=None):
    """Return counts only. Raw CPU counters and MMC3 register values stay local."""
    if cycles is not None and len(events) != len(cycles):
        raise ValueError('Event/cycle list mismatch')
    counts = {region: 0 for region in REGIONS}
    families = {region: {family: 0 for family in FAMILIES}
                for region in REGIONS}
    selector = starting_selector
    previous_cycle = None
    equal_adjacent = 0
    for i, (_frame, address, value) in enumerate(events):
        cycle = cycles[i] if cycles is not None else None
        if (cycle is not None and previous_cycle is not None
                and cycle < previous_cycle):
            raise ValueError('CPU clock decreased within verified event window')
        if cycle is not None and cycle == previous_cycle:
            equal_adjacent += 1
        region = bracket(cycle, previous_clock, current_clock)
        family = event_family(address, selector)
        counts[region] += 1
        families[region][family] += 1
        if 0x8000 <= address <= 0x9FFF and address % 2 == 0:
            selector = value & 7
        previous_cycle = cycle
    if sum(counts.values()) != len(events):
        raise ValueError('Incomplete timestamp bracketing')
    return {
        'registered_callbacks': len(events),
        'cpu_timestamp_group_counts': counts,
        'cpu_timestamp_group_family_counts': families,
        'equal_adjacent_cpu_cycles_within_pair': equal_adjacent,
        'callback_order_known': True,
        'ppu_raster_timing_known': False,
        'scanline_numbers_available': False,
    }, selector


def analyze_verified(session_meta, *, require_cycle=False,
                     require_clock_anchors=False, require_screen_pair=False):
    """Reject incomplete/altered sessions before reading CPU clocks or snapshots."""
    session_meta = Path(session_meta)
    # Stage93 validates the whole session and independently cross-links
    # Stage92 screen pairs and Stage90 committed callback-event windows.
    temporal = temporal_audit(
        session_meta, require_cycle=require_cycle,
        require_screen_pair=require_screen_pair)
    proof = verify(session_meta, require_cycle=require_cycle)
    if proof['session_id'] != temporal['session_id']:
        raise ValueError('Verified session identity changed during analysis')
    if len(proof['capture_frames']) != temporal['snapshot_pairs'] + 1:
        raise ValueError('Snapshot pair/window count mismatch')
    session = metadata(session_meta)
    mode = session['frame_callback_clock_mode']
    anchored = mode == 'sampled_snapshots_v1'
    if require_clock_anchors and not anchored:
        raise ValueError('No verified registerafter snapshot clock anchors')
    events = read_frame_events(session_meta.parent / 'mmc3_video_writes.tsv')
    cycles = (check_cycle_events(
        session_meta.parent / 'mmc3_ppu_cycles.tsv', events)['cycles']
        if proof['cycles_checked'] else None)
    if anchored and cycles is None:
        raise ValueError('Snapshot CPU clock anchors require verified cycle log')

    checkpoints = []
    clocks = []
    for frame in proof['capture_frames']:
        frame_meta = metadata(
            str(session_meta.parent / f'frame_{frame:06d}') + '.meta.txt')
        checkpoints.append(int(frame_meta['logged_register_writes']))
        clocks.append(int(frame_meta['frame_callback_cpu_cycle'])
                      if anchored else None)
    if len(events) < checkpoints[-1]:
        raise ValueError('Snapshot checkpoint exceeds verified event count')

    # Warm the MMC3 selector with the *first* captured snapshot prefix;
    # it is permitted to be unknown until an actual selector callback occurs.
    selector = None
    for _frame, address, value in events[:checkpoints[0]]:
        if 0x8000 <= address <= 0x9FFF and address % 2 == 0:
            selector = value & 7

    pairs = []
    for i, prior in enumerate(temporal['pairs'], 1):
        start, stop = checkpoints[i - 1], checkpoints[i]
        first, last = proof['capture_frames'][i - 1:i + 1]
        if (prior['from_snapshot_frame'] != first
                or prior['to_snapshot_frame'] != last
                or stop < start):
            raise ValueError('Cross-snapshot event checkpoint mismatch')
        subset = events[start:stop]
        cycle_subset = cycles[start:stop] if cycles is not None else None
        evidence, selector = summarize_bracket(
            subset, cycle_subset, starting_selector=selector,
            previous_clock=clocks[i - 1], current_clock=clocks[i])
        if evidence['registered_callbacks'] != prior['callback_window'][
                'registered_callbacks']:
            raise ValueError('Stage93 event-window count disagreement')
        expected_families = prior['callback_window']['counts_by_family']
        for family in FAMILIES:
            if sum(row[family] for row in evidence[
                    'cpu_timestamp_group_family_counts'].values()
                   ) != expected_families[family]:
                raise ValueError('Stage93 callback family classification disagreement')
        pairs.append({
            'from_snapshot_frame': first,
            'to_snapshot_frame': last,
            'saved_callback_frame_distance': last - first,
            'screen_and_callback_relation':
                prior['screen_and_callback_relation'],
            'screen_reference_pair_status':
                prior['screen_reference_pair_status'],
            'known_changed_screen_cells':
                prior['known_changed_screen_cells'],
            'sampled_callback_clock_anchors_present': anchored,
            'snapshot_sample_timestamps_equal':
                clocks[i - 1] == clocks[i] if anchored else None,
            'clock_evidence': evidence,
            'events_at_clock_boundary_are_raster_boundary_events': False,
            'ppu_visible_scanline_position_verified': False,
            'chr_or_scroll_visibility_proven': False,
            'camera_displacement_inferred': False,
            'level_geometry_reconstruction_ready_cells': 0,
        })

    return {
        'format': 'vpd_verified_ppu_cpu_clock_bracketing_v1',
        'session_verified': True,
        'session_id': proof['session_id'],
        'snapshot_pairs': len(pairs),
        'verified_cpu_cycle_log': proof['cycles_checked'],
        'verified_snapshot_clock_anchors': anchored,
        'physical_frame_boundary_proven': False,
        'pairs': pairs,
        'interpretation': {
            'measurement':
                'CPU event timestamps bracketed by registerafter snapshot CPU clock samples',
            'clock_samples_are_ppu_vblank_or_scanline_boundaries': False,
            'CPU_cycles_converted_to_scanlines': False,
            'cycle_equality_resolves_event_order_within_same_timestamp': False,
            'physical_ppu_visible_bank_or_scroll_mapping_proven': False,
            'camera_motion_reconstructed': False,
            'first_level_geometry_proven': False,
            'raw_game_pixels_or_cpu_register_values_exported': False,
        },
        'next_evidence_required': [
            'Independently instrument actual PPU scanline and VBlank position',
            'Tie CHR and scroll state to visible pixels during rasterization',
            'Separate sprite and background pixel ownership',
            'Authenticate private first-level capture before reconstruction',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session_meta', type=Path)
    parser.add_argument('--require-cycle', action='store_true')
    parser.add_argument('--require-clock-anchors', action='store_true')
    parser.add_argument('--require-screen-pair', action='store_true')
    parser.add_argument('--out', type=Path, help='Local private aggregate report')
    args = parser.parse_args()
    result = analyze_verified(
        args.session_meta,
        require_cycle=args.require_cycle,
        require_clock_anchors=args.require_clock_anchors,
        require_screen_pair=args.require_screen_pair)
    report = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding='utf8')
    print(report, end='')


if __name__ == '__main__':
    main()
