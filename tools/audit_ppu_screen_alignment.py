#!/usr/bin/env python3
"""Quantify static screen-layer hypotheses against a verified private FCEUX session.

Results are numerical comparisons, NOT recovered NES raster timing, scrolling,
game level geometry, character sprites or commercial graphics. Private PPU,
RAM, RGB and palette captures must never be committed to public GitHub.
"""
import argparse
import json
from pathlib import Path

from compare_rendered_frame import (
    PIXELS, load_reference, meta_byte, reconstructed_indices,
)
from verify_ppu_capture_session import metadata, verify
from audit_ppu_event_provenance import audit_verified as audit_event_provenance


def compare_index_buffers(candidate, observed):
    """Return only counts; 254 means the reference pixel is unavailable."""
    if len(candidate) != PIXELS or len(observed) != PIXELS:
        raise ValueError('Expected two full 256x240 NES palette-index planes')
    comparable = mismatches = 0
    for predicted, actual in zip(candidate, observed):
        if actual == 254:
            continue
        comparable += 1
        mismatches += predicted != actual
    return {
        'comparable_pixels': comparable,
        'matching_pixels': comparable - mismatches,
        'different_pixels': mismatches,
        'unknown_reference_pixels': PIXELS - comparable,
        'mismatch_fraction': round(mismatches/comparable, 6)
                             if comparable else None,
    }


def compare_frame(prefix):
    """Only evaluate the explicit unscrolled background hypothesis.

    MMC3 mid-frame changes, scroll splits, sprites, mirroring and timing are
    *not* reconstructed; even a perfect candidate is never provenance proof.
    """
    prefix = Path(prefix)
    meta = metadata(str(prefix)+'.meta.txt')
    if meta.get('screen_reference') != 'yes':
        raise ValueError('A verified screen reference is required')
    ppu = Path(str(prefix)+'.ppu.bin').read_bytes()
    ram = Path(str(prefix)+'.ram.bin').read_bytes()
    _rgb, observed = load_reference(prefix)
    ctrl = meta_byte(meta, 'ppuctrl')
    mask = meta_byte(meta, 'ppumask')
    pattern_bases = ([0x1000 if ctrl & 0x10 else 0]
                     if ctrl is not None else [0, 0x1000])
    candidates = []
    for nametable in range(4):
        for base in pattern_bases:
            predicted = reconstructed_indices(
                ppu, ram, nametable, base, sprites=False, mask=mask,
                scroll_x=0, scroll_y=0)
            counts = compare_index_buffers(predicted, observed)
            candidates.append({
                'nametable_window': nametable,
                'background_pattern_base': f'0x{base:04X}',
                **counts,
                'static_scroll_x_assumed': 0,
                'static_scroll_y_assumed': 0,
                'sprites_included': False,
            })
    candidates.sort(key=lambda c: (
        c['different_pixels'] if c['comparable_pixels'] else PIXELS + 1,
        c['nametable_window'], c['background_pattern_base']))
    comparable = candidates[0]['comparable_pixels'] if candidates else 0
    lowest = candidates[0]['different_pixels'] if comparable else None
    tied = (sum(1 for c in candidates if c['different_pixels'] == lowest)
            if lowest is not None else 0)
    return {
        'frame': int(meta['frame']),
        'reference_status': 'verified_screen_file',
        'known_reference_pixels': comparable,
        'unknown_reference_pixels': PIXELS - comparable,
        'static_hypotheses_tested': len(candidates),
        'lowest_error_hypothesis': candidates[0] if comparable else None,
        'hypotheses_tied_for_lowest_error': tied,
        'all_tested_hypotheses': candidates,
        'evidence_classification': {
            'ppu_memory': 'verified_snapshot_bytes',
            'screen_palette_indices': 'verified_reference_bytes',
            'frame_label': 'verified_session_metadata',
            'ppuctrl': ('observed_at_snapshot' if ctrl is not None
                        else 'unknown_both_pattern_bases_tested'),
            'ppumask': ('observed_at_snapshot' if mask is not None
                        else 'unknown_rendering_mask'),
            'scroll': 'unverified_zero_scroll_assumption',
            'nametable_selection': 'tested_hypotheses_not_proven',
            'chr_mapping_during_render': 'unverified',
            'sprites': 'excluded',
            'frame_raster_timing': 'unverified',
            'level_geometry': 'unverified',
        },
    }


def analyze_verified(session_meta, require_cycle=False, require_screen=False):
    """Validate the whole private session *before* using any captured pixels."""
    session_meta = Path(session_meta)
    proof = verify(session_meta, require_cycle=require_cycle)
    # Bind each static image comparison to the exact CPU-event prefix window.
    # This does NOT establish raster-time visibility of any write.
    provenance = audit_event_provenance(session_meta, require_cycle=require_cycle)
    if len(provenance['windows']) != len(proof['capture_frames']):
        raise ValueError('Snapshot/event-window cardinality mismatch')
    entries = []
    available = 0
    for frame, window in zip(proof['capture_frames'], provenance['windows']):
        if window['to_snapshot_frame'] != frame:
            raise ValueError('Snapshot/event-window frame mismatch')
        prefix = session_meta.parent / f'frame_{frame:06d}'
        meta = metadata(str(prefix)+'.meta.txt')
        if meta['screen_reference'] == 'yes':
            available += 1
            comparison = compare_frame(prefix)
            comparison['observed_event_window'] = {
                'observed_cpu_register_events': window['observed_register_events'],
                'chr_register_writes': window['event_counts']['chr_register_writes'],
                'ppuscroll_writes': window['event_counts']['ppuscroll_writes'],
                'complete_observed_ppuscroll_pairs':
                    window['event_counts']['complete_observed_ppuscroll_pairs'],
                'all_six_chr_registers_observed_since_start':
                    window['observed_register_state_at_checkpoint'][
                        'all_six_chr_registers_observed_since_start'],
                'visible_scroll_or_chr_mapping_proven': False,
            }
            entries.append(comparison)
        else:
            entries.append({
                'frame': frame,
                'reference_status': 'not_captured',
                'static_hypotheses_tested': 0,
                'lowest_error_hypothesis': None,
                'observed_event_window': {
                    'observed_cpu_register_events': window['observed_register_events'],
                    'chr_register_writes': window['event_counts']['chr_register_writes'],
                    'ppuscroll_writes': window['event_counts']['ppuscroll_writes'],
                    'complete_observed_ppuscroll_pairs':
                        window['event_counts']['complete_observed_ppuscroll_pairs'],
                    'all_six_chr_registers_observed_since_start':
                        window['observed_register_state_at_checkpoint'][
                            'all_six_chr_registers_observed_since_start'],
                    'visible_scroll_or_chr_mapping_proven': False,
                },
                'evidence_classification': {
                    'screen_palette_indices': 'absent_not_inferred',
                },
            })
    if require_screen and not available:
        raise ValueError('No verified rendered-screen references in session')
    return {
        'format': 'vpd_verified_screen_layer_comparison_v1',
        'session_verified': True,
        'session_id': proof['session_id'],
        'frames_captured': proof['frames_captured'],
        'screen_reference_frames': available,
        'cpu_cycle_trace_verified': proof['cycles_checked'],
        'event_windows_verified': len(provenance['windows']),
        'events_after_last_snapshot': provenance['events_after_last_snapshot'],
        'frames': entries,
        'interpretation': {
            'measurement': 'Static predicted palette indices compared to saved FCEUX indices',
            'ranking': 'Lowest mismatch of explicitly tested hypotheses, not authentic layout',
            'no_reference_policy': 'No inferred or synthetic reference pixels',
            'physical_frame_boundaries_proven': False,
            'actual_scroll_proven': False,
            'event_window_to_screen_visibility_proven': False,
            'chr_midframe_mapping_proven': False,
            'sprites_reconstructed': False,
            'first_level_identity_proven': False,
            'level_geometry_reconstructed': False,
        },
        'limitations': [
            'The 4 nametable windows may be mirrored, not independent layouts',
            'Background CHR table choice is from snapshot PPUCTRL or both tested',
            'Zero scroll is an unverified assumption, not extracted camera motion',
            'Sprites, split scroll, mid-frame bank switching and raster behavior are excluded',
            'A perfect static pixel match does not prove authentic frame or level geometry',
            'Reference pixels marked 254 are excluded from error fractions',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session_meta', type=Path,
                        help='Local private/ppu_capture_session.meta.txt')
    parser.add_argument('--require-cycle', action='store_true')
    parser.add_argument('--require-screen', action='store_true',
                        help='Reject otherwise valid sessions without saved reference screens')
    parser.add_argument('--out', type=Path,
                        help='Save private summary JSON; no raw capture pixels are output')
    args = parser.parse_args()
    summary = analyze_verified(args.session_meta, args.require_cycle,
                               args.require_screen)
    output = json.dumps(summary, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding='utf8')
    print(output, end='')


if __name__ == '__main__':
    main()
