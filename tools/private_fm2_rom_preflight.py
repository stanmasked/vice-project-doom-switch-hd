#!/usr/bin/env python3
"""Owner-local ROM/FM2 compatibility check; never emits original media or hashes."""
import argparse
import base64
import hashlib
from pathlib import Path


def inspect(rom_path: Path, movie_path: Path) -> dict:
    rom = rom_path.read_bytes()
    if len(rom) < 16 or rom[:4] != b'NES\x1a':
        raise ValueError('Not an iNES ROM')
    if rom[6] & 0x04:
        raise ValueError('Trainer ROM not supported by this preflight')
    payload = rom[16:]
    movie = movie_path.read_bytes()
    header = movie.split(b'|', 1)[0].decode('ascii', errors='replace')
    metadata = {}
    for line in header.splitlines():
        parts = line.split(' ', 1)
        if len(parts) == 2:
            metadata[parts[0]] = parts[1].strip()
    checksum = metadata.get('romChecksum', '')
    if not checksum.startswith('base64:'):
        raise ValueError('FM2 romChecksum is missing or not base64')
    expected = base64.b64decode(checksum[7:], validate=True)
    if len(expected) != 16:
        raise ValueError('Unexpected ROM checksum length')
    if hashlib.md5(payload).digest() != expected:
        raise ValueError('ROM checksum does not match FM2; refuse replay')
    frame_count = sum(1 for line in movie.splitlines() if line.startswith(b'|'))
    if frame_count < 321:
        raise ValueError('FM2 is shorter than requested first 321 frames')
    if metadata.get('version') != '3':
        raise ValueError('Expected FM2 version 3')
    return {'rom_matches_movie': True, 'fm2_version': 3,
            'frame_count': frame_count, 'first_321_available': True,
            'private_assets_published': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', required=True, type=Path)
    parser.add_argument('--fm2', required=True, type=Path)
    args = parser.parse_args()
    result = inspect(args.rom, args.fm2)
    print('VPD_PRIVATE_ROM_FM2_PREFLIGHT_PASS ' +
          ' '.join(f'{key}={value}' for key, value in result.items()))


if __name__ == '__main__':
    main()
