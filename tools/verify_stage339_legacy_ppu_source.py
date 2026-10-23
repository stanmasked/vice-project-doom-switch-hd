#!/usr/bin/env python3
"""Fail-closed source contract for the exact FCEUX v2.6.5 classic PPU core.

This checks a local copy of upstream src/ppu.cpp *before* making a diagnostic
patch. It cannot by itself demonstrate a PPU-dot witness or even a built binary.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

FCEUX_TAG = 'v2.6.5'
UPSTREAM_TAG_COMMIT = 'ea6ed69b874e3ae94072f1b4f14b9a8f0fdd774b'
UPSTREAM_PPU_BLOB = 'aa7502eb956595c29096856ab8beddb5eecc301b'
UPSTREAM_SOURCE = 'src/ppu.cpp'
REQUIRED = (
    'int newppu = 0;',
    'uint8 vtoggle = 0;',
    'uint32 TempAddr = 0, RefreshAddr = 0',
    'static INLINE void Fixit2(void)',
    'static void DoLine(void)',
    'static DECLFW(B2005)',
    'static DECLFW(B2006)',
    'uint32 FCEUPPU_PeekAddress()',
    'return RefreshAddr & 0x3FFF;',
)


def verify(path: Path, *, expected_blob_sha: str=UPSTREAM_PPU_BLOB) -> dict[str, object]:
    if path.is_symlink() or not path.is_file() or not 1000 <= path.stat().st_size <= 250_000:
        raise ValueError('missing or invalid upstream source file')
    b=path.read_bytes()
    actual=hashlib.sha1(f'blob {len(b)}\0'.encode('ascii')+b).hexdigest()
    if actual != expected_blob_sha:
        raise ValueError('upstream PPU file differs from pinned FCEUX v2.6.5 blob')
    try:
        source=b.decode('utf-8')
    except UnicodeError as exc:
        raise ValueError('unexpected upstream source encoding') from exc
    for anchor in REQUIRED:
        if source.count(anchor) != 1:
            raise ValueError('missing/ambiguous original legacy PPU source anchor')
    if source.count('static void Fixit1(void)') != 2 or source.count('if (newppu)') < 1:
        raise ValueError('legacy PPU source declarations or core gate missing')
    if source.find('static INLINE void Fixit2(void)') > source.find('static void DoLine(void)'):
        raise ValueError('legacy PPU source layout changed')
    return {
        'format':'vpd_stage339_legacy_ppu_upstream_contract_v1',
        'upstream_tag': FCEUX_TAG,
        'pinned_upstream_source_verified': True,
        'classic_refreshaddr_present': True,
        'classic_scanline_present': True,
        'newppu_dot_getter_separate_from_legacy_mode': True,
        'instrumented_emulator_built': False,
        'actual_ppu_dot_observed': False,
        'private_upstream_file_contents_disclosed': False
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ppu-source',required=True,type=Path)
    a=p.parse_args()
    try:
        print(json.dumps(verify(a.ppu_source),sort_keys=True,indent=2))
    except (OSError,ValueError):
        p.exit(1,'VPD_STAGE339_UPSTREAM_CONTRACT_INCONCLUSIVE\n')

if __name__ == '__main__': main()
