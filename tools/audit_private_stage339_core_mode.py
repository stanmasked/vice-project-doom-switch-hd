#!/usr/bin/env python3
"""Stage339: authenticate the owner's original FM2 PPU mode without changing it.

This script is deliberately a *preflight*, not a scanline/dot-level PPU witness.
It prints only non-sensitive aggregate facts, never FM2 header identifiers,
source hashes, paths, controller input, or original gameplay values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

MAX_FM2_BYTES = 32_000_000
FIELDS = ('version', 'emuVersion', 'palFlag', 'NewPPU')


def parse_fm2(path: Path, *, expected_sha256: str | None = None) -> dict[str, object]:
    if path.is_symlink() or not path.is_file() or not (1 <= path.stat().st_size <= MAX_FM2_BYTES):
        raise ValueError('FM2 missing, linked, empty, or oversized')
    if expected_sha256 is not None:
        if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
            raise ValueError('invalid private source hash')
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != expected_sha256:
            raise ValueError('FM2 full-file SHA-256 mismatch')
    seen: dict[str, str] = {}
    frames = 0
    in_inputs = False
    with path.open('rb') as stream:
        for raw in stream:
            if len(raw) > 100_000:
                raise ValueError('oversized FM2 line')
            if raw.startswith(b'|'):
                in_inputs = True
                # Every input record is one frame; no need to retain controller data.
                frames += 1
                continue
            if in_inputs:
                if raw.strip():
                    raise ValueError('non-input data after FM2 input begins')
                continue
            if not raw.strip() or raw.startswith(b'#'):
                continue
            try:
                text = raw.decode('ascii').rstrip('\r\n')
            except UnicodeError as exc:
                raise ValueError('FM2 header contains non-ASCII data') from exc
            if ' ' not in text:
                raise ValueError('malformed FM2 header')
            key, value = text.split(' ', 1)
            if not key or not value or key in seen:
                raise ValueError('duplicate, blank or invalid FM2 header key')
            seen[key] = value
    if not set(FIELDS).issubset(seen) or frames == 0:
        raise ValueError('required PPU mode, emulator version or input data missing')
    for key in FIELDS:
        if not seen[key].isdecimal():
            raise ValueError('non-numeric FM2 mode/version field')
    if seen['version'] != '3':
        raise ValueError('unsupported FM2 version')
    if seen['palFlag'] not in ('0','1') or seen['NewPPU'] not in ('0','1'):
        raise ValueError('invalid FM2 PPU or television flag')
    return {
        'format': 'vpd_stage339_owner_fm2_ppu_mode_gate_v1',
        'fm2_format_v3': True,
        'input_records': frames,
        'ntsc_source': seen['palFlag'] == '0',
        'legacy_ppu_source': seen['NewPPU'] == '0',
        'experimental_newppu_source': seen['NewPPU'] == '1',
        'fceux_v265_source_label_verified': False,  # Header version alone is not a binary identity.
        'ppu_scanline_dot_observed': False,
        'actual_ppu_v_observed': False,
        'rendered_scroll_proven': False,
        'private_bytes_or_hashes_disclosed': False,
    }


def enforce_legacy_ntsc(result: dict[str, object], expected_frames: int | None = None) -> dict[str, object]:
    if not result['ntsc_source'] or not result['legacy_ppu_source']:
        raise ValueError('source FM2 PPU core/TV mode is not legacy NTSC; do not switch cores')
    if expected_frames is not None and result['input_records'] != expected_frames:
        raise ValueError('FM2 original movie input count mismatch')
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--movie', type=Path, required=True)
    p.add_argument('--source-sha256', required=True)
    p.add_argument('--expected-frames', type=int, default=43652)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    try:
        summary = enforce_legacy_ntsc(parse_fm2(a.movie, expected_sha256=a.source_sha256), a.expected_frames)
        payload = json.dumps(summary, sort_keys=True, indent=2) + '\n'
        if a.output:
            if a.output.exists() or a.output.is_symlink():
                raise ValueError('refusing existing or linked report')
            with a.output.open('x', encoding='utf-8') as out:
                out.write(payload)
        else:
            print(payload, end='')
    except (ValueError, OSError, UnicodeError) as exc:
        p.exit(1, 'VPD_STAGE339_SOURCE_MODE_INCONCLUSIVE: source identity or mode differs\n')

if __name__ == '__main__':
    main()
