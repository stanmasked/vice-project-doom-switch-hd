#!/usr/bin/env python3
"""Stage91: conservative readiness triage for verified FCEUX background observations.

A 8x8 screen-cell match is a *static candidate* only. No inferred tile atlas,
camera path, raster-accurate bank mapping, ROM identity, or level geometry.
Outputs aggregate counts only; keep private capture reports off public GitHub.
"""
import argparse
import json
from pathlib import Path

from audit_ppu_event_provenance import audit_verified as event_audit
from compare_rendered_frame import PIXELS, load_reference, meta_byte, reconstructed_indices
from verify_ppu_capture_session import metadata, verify

CELL = 8
WIDTH, HEIGHT = 256, 240
TOTAL_CELLS = (WIDTH // CELL) * (HEIGHT // CELL)
CLASSES = (
    'unassessed_no_reference',
    'incomplete_reference',
    'unanimous_static_match',
    'hypothesis_dependent_static_match',
    'no_exact_static_match',
)


def classify_cells(reference, candidates):
    """Count mutually exclusive 8x8 screen areas; never expose their positions.

    Full 64-pixel exact matches are required. Pixels with value 254 are
    unknown, not mismatches. A match is never a reconstructed game tile.
    """
    if len(reference) != PIXELS or not candidates:
        raise ValueError('Expected full reference plane and static hypotheses')
    if any(len(candidate) != PIXELS for candidate in candidates):
        raise ValueError('Static hypothesis has an invalid image length')
    if any(value > 63 and value != 254 for value in reference):
        raise ValueError('Invalid reference NES palette index')
    counts = {name: 0 for name in CLASSES}
    for y in range(0, HEIGHT, CELL):
        for x in range(0, WIDTH, CELL):
            positions = [row * WIDTH + col
                         for row in range(y, y + CELL)
                         for col in range(x, x + CELL)]
            if any(reference[i] == 254 for i in positions):
                counts['incomplete_reference'] += 1
                continue
            matching = sum(all(candidate[i] == reference[i] for i in positions)
                           for candidate in candidates)
            if matching == len(candidates):
                counts['unanimous_static_match'] += 1
            elif matching:
                counts['hypothesis_dependent_static_match'] += 1
            else:
                counts['no_exact_static_match'] += 1
    assert sum(counts.values()) == TOTAL_CELLS
    return counts


def static_candidates(prefix, frame_meta):
    """Replicate stage89's limited zero-scroll background hypothesis family."""
    ppu = Path(str(prefix) + '.ppu.bin').read_bytes()
    ram = Path(str(prefix) + '.ram.bin').read_bytes()
    ctrl = meta_byte(frame_meta, 'ppuctrl')
    mask = meta_byte(frame_meta, 'ppumask')
    pattern_bases = ([0x1000 if ctrl & 0x10 else 0]
                     if ctrl is not None else [0, 0x1000])
    return [reconstructed_indices(ppu, ram, nt, base,
                                  sprites=False, mask=mask,
                                  scroll_x=0, scroll_y=0)
            for nt in range(4) for base in pattern_bases]


def risk_from_window(window):
    """Expose only which crucial raster facts remain unproven, not values."""
    counts = window['event_counts']
    state = window['observed_register_state_at_checkpoint']
    return {
        'observed_chr_data_writes': counts['chr_register_writes'],
        'observed_ppuscroll_writes': counts['ppuscroll_writes'],
        'observed_complete_scroll_pairs':
            counts['complete_observed_ppuscroll_pairs'],
        'observed_ppuaddr_writes': counts['ppuaddr_writes'],
        'observed_chr_inversion_changes':
            counts['chr_inversion_changes_observed'],
        'unknown_mmc3_selector_writes':
            counts['mmc3_data_writes_without_known_selector'],
        'all_six_chr_registers_observed_since_start':
            state['all_six_chr_registers_observed_since_start'],
        'scroll_latch_synchronized':
            state['ppuscroll_write_toggle_synchronized'],
        'visible_scroll_proven': False,
        'scanline_chr_mapping_proven': False,
        'event_to_raster_alignment_proven': False,
    }


def analyze_verified(session_meta, *, require_cycle=False, require_screen=False):
    """Validate the *entire* session before opening individual PPU/screen blobs."""
    session_meta = Path(session_meta)
    proof = verify(session_meta, require_cycle=require_cycle)
    provenance = event_audit(session_meta, require_cycle=require_cycle)
    if len(provenance['windows']) != len(proof['capture_frames']):
        raise ValueError('Verified frame/provenance window count mismatch')
    frames = []
    screens = 0
    for frame, window in zip(proof['capture_frames'], provenance['windows']):
        if window['to_snapshot_frame'] != frame:
            raise ValueError('Provenance window misaligned with captured frame')
        prefix = session_meta.parent / f'frame_{frame:06d}'
        meta = metadata(str(prefix) + '.meta.txt')
        exists = meta['screen_reference'] == 'yes'
        if exists:
            screens += 1
            _rgb, observed = load_reference(prefix)
            candidates = static_candidates(prefix, meta)
            classes = classify_cells(observed, candidates)
        else:
            candidates = []
            classes = {name: (TOTAL_CELLS if name == 'unassessed_no_reference'
                              else 0) for name in CLASSES}
        matching = (classes['unanimous_static_match']
                    + classes['hypothesis_dependent_static_match'])
        frames.append({
            'frame': frame,
            'reference_status': ('verified_saved_screen' if exists
                                 else 'not_captured'),
            'static_hypotheses_tested': len(candidates),
            'evaluated_screen_cells': TOTAL_CELLS if exists else 0,
            'screen_cell_counts': classes,
            'static_exact_match_candidate_cells': matching,
            'reconstruction_ready_cells': 0,
            'background_evidence': ('static_zero_scroll_candidates_only'
                                    if exists and matching
                                    else 'no_supported_static_background_cells'),
            'event_window': {
                'observed_cpu_register_events': window['observed_register_events'],
                **risk_from_window(window),
            },
            'raster_visible_background_proven': False,
            'world_level_coordinates_proven': False,
        })
    if require_screen and not screens:
        raise ValueError('No verified screen references in session')
    totals = {name: sum(f['screen_cell_counts'][name] for f in frames)
              for name in CLASSES}
    return {
        'format': 'vpd_verified_background_readiness_v1',
        'session_verified': True,
        'session_id': proof['session_id'],
        'frames_captured': len(frames),
        'screen_reference_frames': screens,
        'cpu_cycle_trace_verified': proof['cycles_checked'],
        'total_screen_cells_accounted_for': TOTAL_CELLS * len(frames),
        'aggregate_cell_counts': totals,
        'reconstruction_ready_cells': 0,
        'frames': frames,
        'evidence_rules': {
            'cell_size_pixels': CELL,
            'unknown_reference_index': 254,
            'only_fully_known_64_pixel_cells_can_match': True,
            'zero_scroll_and_snapshot_chr_are_unproven_hypotheses': True,
            'candidate_consensus_is_not_raster_or_geometry_proof': True,
            'candidate_matches_do_not_identify_game_background_vs_sprites': True,
            'original_game_identity_authenticated': False,
            'first_level_layout_reconstructed': False,
            'physical_ppu_frame_boundaries_proven': False,
            'raw_pixel_or_register_values_in_report': False,
        },
        'next_evidence_required': [
            'Independent identity and first-level provenance for private capture',
            'Raster-aligned scroll and MMC3 CHR mapping observations',
            'Sprite/background separation for visible screen references',
            'Cross-frame tile and camera continuity verified before asset extraction',
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('session_meta', type=Path)
    p.add_argument('--require-cycle', action='store_true')
    p.add_argument('--require-screen', action='store_true')
    p.add_argument('--out', type=Path,
                   help='Local private numeric report only; never commit captures')
    args = p.parse_args()
    result = analyze_verified(args.session_meta,
                              require_cycle=args.require_cycle,
                              require_screen=args.require_screen)
    output = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding='utf8')
    print(output, end='')


if __name__ == '__main__':
    main()
