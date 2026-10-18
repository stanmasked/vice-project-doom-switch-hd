#!/usr/bin/env python3
"""Audit observed MMC3 CHR and PPU scroll writes between verified snapshots.

A register-write sequence is evidence of CPU callbacks, NOT actual PPU raster
state. The numeric report deliberately omits raw original game values.
"""
import argparse
import json
from pathlib import Path

from verify_ppu_capture_session import metadata, read_frame_events, verify


class RegisterObservation:
    """Replay only the CPU register writes actually recorded in FCEUX."""

    def __init__(self):
        self.selected_chr_register = None
        self.chr_inversion = None
        self.observed_chr_regs = set()
        self.ppuctrl = None
        self.scroll_latch = None       # None until first observed PPUSTATUS read
        self.pending_scroll_x = False
        self.complete_scroll_pairs = 0

    def observe(self, frame, address, value, counters):
        if 0x8000 <= address <= 0x9FFF:
            if address % 2 == 0:
                counters['mmc3_select_writes'] += 1
                next_inversion = bool(value & 0x80)
                if (self.chr_inversion is not None
                        and next_inversion != self.chr_inversion):
                    counters['chr_inversion_changes_observed'] += 1
                self.chr_inversion = next_inversion
                self.selected_chr_register = value & 7
            else:
                counters['mmc3_data_writes'] += 1
                if self.selected_chr_register is None:
                    counters['mmc3_data_writes_without_known_selector'] += 1
                elif self.selected_chr_register <= 5:
                    counters['chr_register_writes'] += 1
                    self.observed_chr_regs.add(self.selected_chr_register)
                else:
                    counters['prg_register_data_writes'] += 1
        if not 0x2000 <= address <= 0x3FFF:
            return
        port = (address - 0x2000) % 8
        if port == 0:
            counters['ppuctrl_writes'] += 1
            if self.ppuctrl is not None and ((self.ppuctrl ^ value) & 0x10):
                counters['ppuctrl_bg_pattern_bit_changes'] += 1
            self.ppuctrl = value
        elif port == 2:
            counters['ppustatus_read_markers'] += 1
            if self.pending_scroll_x:
                counters['interrupted_scroll_first_writes'] += 1
            self.scroll_latch = 0
            self.pending_scroll_x = False
        elif port == 6:
            counters['ppuaddr_writes'] += 1
            if self.pending_scroll_x:
                counters['interrupted_scroll_first_writes'] += 1
            self.pending_scroll_x = False
            if self.scroll_latch is not None:
                self.scroll_latch = 1 - self.scroll_latch
        elif port == 5:
            counters['ppuscroll_writes'] += 1
            if self.scroll_latch is None:
                counters['ppuscroll_writes_before_latch_sync'] += 1
            elif self.scroll_latch == 0:
                self.pending_scroll_x = True
                self.scroll_latch = 1
            else:
                if self.pending_scroll_x:
                    counters['complete_observed_ppuscroll_pairs'] += 1
                    self.complete_scroll_pairs += 1
                else:
                    counters['ppuscroll_second_writes_without_known_first'] += 1
                self.pending_scroll_x = False
                self.scroll_latch = 0

    def checkpoint(self):
        return {
            'chr_selector_observed': self.selected_chr_register is not None,
            'chr_inversion_observed': self.chr_inversion is not None,
            'distinct_chr_registers_observed_since_start': len(self.observed_chr_regs),
            'all_six_chr_registers_observed_since_start':
                len(self.observed_chr_regs) == 6,
            'ppuctrl_observed_since_start': self.ppuctrl is not None,
            'ppuscroll_write_toggle_synchronized': self.scroll_latch is not None,
            'pending_first_ppuscroll_write': self.pending_scroll_x,
            'completed_scroll_pairs_since_start': self.complete_scroll_pairs,
            'rendered_scroll_value_proven': False,
            'ppu_raster_bank_mapping_proven': False,
        }


COUNTERS = (
    'mmc3_select_writes',
    'mmc3_data_writes',
    'mmc3_data_writes_without_known_selector',
    'chr_register_writes',
    'prg_register_data_writes',
    'chr_inversion_changes_observed',
    'ppuctrl_writes',
    'ppuctrl_bg_pattern_bit_changes',
    'ppustatus_read_markers',
    'ppuaddr_writes',
    'ppuscroll_writes',
    'ppuscroll_writes_before_latch_sync',
    'ppuscroll_second_writes_without_known_first',
    'complete_observed_ppuscroll_pairs',
    'interrupted_scroll_first_writes',
)


def audit_verified(session_meta, *, require_cycle=False):
    """Reject incomplete files before attributing any registered write."""
    session_meta = Path(session_meta)
    proof = verify(session_meta, require_cycle=require_cycle)
    events = read_frame_events(session_meta.parent / 'mmc3_video_writes.tsv')
    replay = RegisterObservation()
    windows = []
    checkpoint = 0
    for snapshot in proof['capture_frames']:
        prefix = session_meta.parent / f'frame_{snapshot:06d}'
        frame_meta = metadata(str(prefix)+'.meta.txt')
        stop = int(frame_meta['logged_register_writes'])
        if not checkpoint <= stop <= len(events):
            raise ValueError('Invalid verified snapshot event checkpoint')
        counters = {name: 0 for name in COUNTERS}
        observed_frame_labels = set()
        for frame, address, value in events[checkpoint:stop]:
            if frame > snapshot:
                raise ValueError('Future-labeled event in snapshot window')
            observed_frame_labels.add(frame)
            replay.observe(frame, address, value, counters)
        windows.append({
            'from_snapshot_frame': (
                proof['capture_frames'][len(windows)-1] if windows else None),
            'to_snapshot_frame': snapshot,
            'event_start_index': checkpoint,
            'event_end_index_exclusive': stop,
            'observed_register_events': stop - checkpoint,
            'distinct_event_frame_labels': len(observed_frame_labels),
            'event_counts': counters,
            'observed_register_state_at_checkpoint': replay.checkpoint(),
            'provenance': 'verified_event_log_prefix_and_CPU_register_callbacks',
            'ppu_scanline_timing_proven': False,
            'visible_frame_scroll_proven': False,
            'visible_chr_bank_mapping_proven': False,
            'static_reference_screen_explained': False,
        })
        checkpoint = stop
    trailing = len(events) - checkpoint
    return {
        'format': 'vpd_verified_ppu_event_provenance_v1',
        'session_verified': True,
        'session_id': proof['session_id'],
        'frames_captured': len(windows),
        'events_recorded': len(events),
        'events_after_last_snapshot': trailing,
        'clock_trace_verified': proof['cycles_checked'],
        'windows': windows,
        'interpretation': {
            'records': 'observed CPU callbacks grouped by committed snapshot prefixes',
            'observed_register_values_exported': False,
            'ppu_visible_scroll_proven': False,
            'ppu_raster_chr_banks_proven': False,
            'physical_frame_boundaries_proven': False,
            'level_geometry_reconstructed': False,
        },
        'limitations': [
            'CPU writes are not proof that a value rendered on a particular scanline',
            'Recorded $2002 is a latch-reset marker, not the actual PPUSTATUS bus value',
            'PPUADDR and PPUSCROLL share a write toggle and can interrupt one another',
            'CHR register values and inversion may be unknown until written in this session',
            'MMC3 CHR swaps may happen inside a rendered frame',
            'A change between captured snapshots does not prove a visible on-screen change',
            'No original ROM identity, first-level layout or actual camera position is inferred',
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('session_meta', type=Path,
                   help='Private complete FCEUX ppu_capture_session.meta.txt')
    p.add_argument('--require-cycle', action='store_true')
    p.add_argument('--out', type=Path,
                   help='Local private JSON report; no raw register values')
    args = p.parse_args()
    result = audit_verified(args.session_meta, require_cycle=args.require_cycle)
    output = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding='utf8')
    print(output, end='')


if __name__ == '__main__':
    main()
