#!/usr/bin/env python3
"""Inventory a strictly verified private FCEUX PPU capture session.

This is evidence triage, not a level map, emulated raster trace, decoded
gameplay, or proof that the captured game is Vice: Project Doom.
No original bytes, tile IDs, palettes or images are included in reports.
"""
import argparse
import json
from pathlib import Path

from verify_ppu_capture_session import metadata, verify

PPU_SIZE = 0x4000
RAM_SIZE = 0x800


def count_changed(before, after):
    if len(before) != len(after):
        raise ValueError('Cannot compare regions of different sizes')
    return sum(a != b for a, b in zip(before, after))


def snapshot_regions(ppu, ram):
    if len(ppu) != PPU_SIZE or len(ram) != RAM_SIZE:
        raise ValueError('Expected verified 16 KiB PPU and 2 KiB RAM')
    return {
        'chr_1k_pages': [ppu[i*0x400:(i+1)*0x400] for i in range(8)],
        'nametable_tiles': [
            ppu[0x2000+i*0x400:0x2000+i*0x400+960]
            for i in range(4)
        ],
        'nametable_attributes': [
            ppu[0x2000+i*0x400+960:0x2000+(i+1)*0x400]
            for i in range(4)
        ],
        'palette_bytes': ppu[0x3F00:0x3F20],
        'cpu_ram': ram,
        'ppu': ppu,
        'queue': ram[0x600:0x700],
        'oam_source': ram[0x700:0x800],
    }


def compare_regions(before, after):
    """Numerical evidence only. No reconstructed tiles or sprite identities."""
    a, b = before, after
    return {
        'ppu_changed_bytes': count_changed(a['ppu'], b['ppu']),
        'ram_changed_bytes': count_changed(a['cpu_ram'], b['cpu_ram']),
        'chr_1k_changed_bytes': [
            count_changed(x, y)
            for x, y in zip(a['chr_1k_pages'], b['chr_1k_pages'])
        ],
        'nametable_tile_cells_changed': [
            count_changed(x, y)
            for x, y in zip(a['nametable_tiles'], b['nametable_tiles'])
        ],
        'nametable_attribute_bytes_changed': [
            count_changed(x, y)
            for x, y in zip(a['nametable_attributes'], b['nametable_attributes'])
        ],
        'palette_memory_bytes_changed': count_changed(
            a['palette_bytes'], b['palette_bytes']),
        'queue_0600_changed_bytes': count_changed(a['queue'], b['queue']),
        'oam_source_0700_changed_slots': sum(
            a['oam_source'][i:i+4] != b['oam_source'][i:i+4]
            for i in range(0, 256, 4)
        ),
    }


def analyze_verified(session_meta, require_cycle=False):
    """Refuse to inventory untrusted or incomplete sessions."""
    session_meta = Path(session_meta)
    proof = verify(session_meta, require_cycle=require_cycle)
    frames = proof['capture_frames']
    if not frames:
        raise ValueError('A verified session must include captured frames')

    snapshots = []
    changes = []
    seen_chr_pages = [set() for _ in range(8)]
    seen_nametable_tiles = [set() for _ in range(4)]
    screen_count = 0
    previous = None
    previous_frame = None

    for frame in frames:
        prefix = session_meta.parent / f'frame_{frame:06d}'
        # All file bytes and metadata were independently validated by verify.
        meta = metadata(str(prefix)+'.meta.txt')
        ppu = Path(str(prefix)+'.ppu.bin').read_bytes()
        ram = Path(str(prefix)+'.ram.bin').read_bytes()
        regions = snapshot_regions(ppu, ram)

        # Distinct raw regions are counted, not published.
        for i, page in enumerate(regions['chr_1k_pages']):
            seen_chr_pages[i].add(page)
        for i, table in enumerate(regions['nametable_tiles']):
            seen_nametable_tiles[i].add(table)
        screen = meta['screen_reference'] == 'yes'
        if screen:
            screen_count += 1
        raw_callback = meta.get('frame_callback_cpu_cycle', 'not_captured')
        callback_cycle = (int(raw_callback)
                          if raw_callback != 'not_captured' else None)
        snapshots.append({
            'frame': frame,
            'rendered_screen_reference_present': screen,
            'registerafter_cpu_cycle_sample': callback_cycle,
            'nametable_nonzero_tile_cells': [
                sum(value != 0 for value in table)
                for table in regions['nametable_tiles']
            ],
            'unique_nametable_tile_id_counts': [
                len(set(table)) for table in regions['nametable_tiles']
            ],
        })
        if previous is not None:
            changes.append({
                'from_frame': previous_frame,
                'to_frame': frame,
                'frame_label_distance': frame - previous_frame,
                'frame_labels_between_snapshots': frame - previous_frame - 1,
                **compare_regions(previous, regions),
            })
        previous = regions
        previous_frame = frame

    return {
        'format': 'vpd_verified_ppu_reference_inventory_v1',
        'session_verified': True,
        'verified_session_id': proof['session_id'],
        'frames_captured': len(frames),
        'recorded_event_count': proof['events_checked'],
        'cpu_cycle_trace_verified': proof['cycles_checked'],
        'rendered_screen_reference_frames': screen_count,
        'snapshot_comparisons': len(changes),
        'distinct_chr_1k_page_versions_by_slot': [
            len(values) for values in seen_chr_pages
        ],
        'distinct_nametable_tile_versions_by_slot': [
            len(values) for values in seen_nametable_tiles
        ],
        'snapshots': snapshots,
        'changes_between_snapshots': changes,
        'capture_provenance': {
            'snapshot_contents_verified': proof['snapshot_bytes_verified'],
            'event_log_contents_verified': proof['event_logs_verified'],
            'physical_frame_boundaries_proven': False,
            'original_rom_identity_authenticated': False,
            'original_first_level_identified': False,
            'nametable_mirroring_resolved': False,
            'level_geometry_reconstructed': False,
            'hd_artwork_reconstructed': False,
        },
        'limitations': [
            'Differences are observed between selected snapshots, not every rendered frame',
            'CHR 1 KiB slots may change via MMC3 bank switches within a frame',
            'Nametable mirroring may duplicate regions; no world coordinates are inferred',
            'Palette memory aliases can make raw changed-byte counts misleading',
            'RAM $0700 is a possible OAM DMA source, not proof of actual visible sprites',
            'A screen reference indicates a saved emulator image, not a validated raster timeline',
            'Actual first-level identity, camera position and gameplay meaning require independent evidence',
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('session_meta', type=Path,
                   help='Local private/ppu_capture_session.meta.txt')
    p.add_argument('--require-cycle', action='store_true',
                   help='Reject sessions without verified CPU-cycle log')
    p.add_argument('--out', type=Path,
                   help='Save summary only; keep any game-derived report private')
    args = p.parse_args()
    report = analyze_verified(args.session_meta, require_cycle=args.require_cycle)
    payload = json.dumps(report, indent=2, ensure_ascii=False) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding='utf8')
    print(payload, end='')


if __name__ == '__main__':
    main()
