#!/usr/bin/env python3
"""Stage95: fail-closed audit of Lua raster symbol-presence probe output.

A function name's presence is not evidence that it reports PPU raster
state, VBlank, scanline position, a rendered pixel, or first-level geometry.
"""
import argparse
import json
from pathlib import Path

FORMAT = 'vpd_fceux_raster_capability_probe_v1'
SYMBOLS = (
    'framecount_symbol',
    'registerbefore_symbol',
    'registerafter_symbol',
    'registerwrite_symbol',
    'cpu_cycle_symbol',
    'ppu_readback_symbol',
    'emu_scanline_candidate',
    'emu_dot_candidate',
    'ppu_scanline_candidate',
    'ppu_dot_candidate',
)
NEGATIVE = (
    'candidate_api_called',
    'register_callbacks_installed',
    'game_memory_accessed',
    'vblank_edge_observed',
    'ppu_scanline_observed',
    'ppu_dot_observed',
    'frame_boundary_proven',
    'visible_chr_scroll_timing_proven',
)


class ProbeError(ValueError):
    pass


def parse_probe(text):
    if not isinstance(text, str) or not text.endswith('\n'):
        raise ProbeError('Missing final newline in probe report')
    entries = {}
    for row in text.splitlines():
        if row.count('=') != 1:
            raise ProbeError('Invalid key/value probe row')
        key, value = row.split('=', 1)
        if not key or key in entries:
            raise ProbeError('Unknown, duplicate or missing probe key')
        entries[key] = value
    expected = {'format', 'probe_scope', *SYMBOLS, *NEGATIVE}
    if set(entries) != expected:
        raise ProbeError('Missing or unexpected probe fields')
    if entries['format'] != FORMAT:
        raise ProbeError('Unexpected raster probe report version')
    if entries['probe_scope'] != 'lua_symbol_presence_only':
        raise ProbeError('Probe scope cannot claim runtime raster measurements')
    for key in SYMBOLS:
        if entries[key] not in ('present', 'absent'):
            raise ProbeError('Invalid capability symbol status: ' + key)
    for key in NEGATIVE:
        if entries[key] != 'no':
            raise ProbeError('Unverified raster or side-effect claim: ' + key)
    return entries


def analyze(text):
    data = parse_probe(text)
    candidates = {
        'scanline': (
            data['emu_scanline_candidate'] == 'present'
            or data['ppu_scanline_candidate'] == 'present'),
        'dot': (
            data['emu_dot_candidate'] == 'present'
            or data['ppu_dot_candidate'] == 'present'),
    }
    prerequisites = {
        'frame_callbacks': data['registerafter_symbol'] == 'present',
        'cpu_cycle_clock': data['cpu_cycle_symbol'] == 'present',
        'register_write_callbacks': data['registerwrite_symbol'] == 'present',
    }
    return {
        'format': 'vpd_fceux_raster_capability_audit_v1',
        'input_probe_validated': True,
        'probe_scope': 'lua_symbol_presence_only',
        'candidate_scanline_function_detected': candidates['scanline'],
        'candidate_dot_function_detected': candidates['dot'],
        'documented_callback_symbol_presence': prerequisites,
        'next_probing_path': (
            'independently_validate_candidate_apis_with_native_ppu_trace'
            if all(candidates.values()) else
            'instrument_native_ppu_scanline_dot_vblank_before_raster_claims'
        ),
        'raster_capability_tested_on_real_fceux': False,
        'candidate_functions_called': False,
        'ppu_scanline_or_dot_values_observed': False,
        'vblank_edge_observed': False,
        'physical_ppu_timing_proven': False,
        'cpu_write_to_raster_visibility_proven': False,
        'first_level_geometry_proven': False,
        'rom_or_graphics_bytes_in_report': False,
        'limitations': [
            'Lua symbol presence is not a functional interface contract',
            'Frame callbacks do not identify a physical VBlank edge',
            'CPU cycle counts are not PPU scanline/dot observations',
            'Actual FCEUX PPU instrumentation needs independent validation',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe_file', type=Path,
                        help='Plain-text preflight captured locally from Lua output')
    parser.add_argument('--out', type=Path,
                        help='Optional local summary with no captured game bytes')
    args = parser.parse_args()
    result = analyze(args.probe_file.read_text(encoding='utf8'))
    payload = json.dumps(result, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding='utf8')
    print(payload, end='')


if __name__ == '__main__':
    main()
