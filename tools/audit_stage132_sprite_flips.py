#!/usr/bin/env python3
"""Pinned FCEUX newppu sprite horizontal/vertical flip source and model audit.

Source-only / Python-model preflight; not a native flipped-sprite XBuf proof.
"""
import argparse
from pathlib import Path


class SpriteFlipError(ValueError):
    pass


FETCH_ANCHORS = (
    'const int spriteHeight = Sprite16 ? 16 : 8;',
    'uint32 line = yp - oam[0];',
    'if (oam[2] & 0x80)',
    'line = spriteHeight - line - 1;',
    'if (Sprite16) {',
    'uint32 bank = (patternNumber & 1) << 12;',
    'patternNumber = patternNumber & ~1;',
    'patternNumber |= (line >> 3);',
    'patternAddress = (patternNumber << 4) | bank;',
    'patternAddress = (patternNumber << 4) | (SpAdrHI << 9);',
    'patternAddress += line & 7;',
    'oam[4] = CALL_PPUREAD(RefreshAddr);',
    'oam[5] = CALL_PPUREAD(RefreshAddr);',
    'if (!(oam[2] & 0x40)) {',
    'oam[4] = bitrevlut[oam[4]];',
    'oam[5] = bitrevlut[oam[5]];',
)
RASTER_ANCHORS = (
    'uint8 spixel = oam[4] & 1;',
    'spixel |= (oam[5] & 1) << 1;',
    'oam[4] >>= 1;',
    'oam[5] >>= 1;',
)


def _ordered_once(source, anchors, limit):
    indexes = []
    for anchor in anchors:
        if source.count(anchor) != 1:
            raise SpriteFlipError('Missing/ambiguous native flip operation: ' + anchor)
        indexes.append(source.index(anchor))
    if indexes != sorted(indexes) or indexes[-1]-indexes[0] > limit:
        raise SpriteFlipError('Pinned FCEUX flip operation order changed')


def verify_source(source):
    if isinstance(source, bytes):
        source = source.decode('latin1')
    if not isinstance(source, str):
        raise SpriteFlipError('Pinned ppu.cpp must be source text')
    _ordered_once(source, FETCH_ANCHORS, 8000)
    _ordered_once(source, RASTER_ANCHORS, 1100)
    if source.index(RASTER_ANCHORS[0]) >= source.index(FETCH_ANCHORS[0]):
        raise SpriteFlipError('Raster/fetch source layout unexpectedly reordered')
    return {'source_revision_pinned': True, 'vertical_flip_source': True,
            'horizontal_reverse_source': True,
            'native_flip_pixels_proven': False,
            'original_game_sprite_flips_proven': False}


def flipped_pattern(*, tile, x, y, low, high, hflip=False, vflip=False,
                    height=8, sprite_table_high=True):
    """Return (palette low two bits, expected CHR low-plane source address).

    low and high are an 8- or 16-byte array of original, unflipped CHR rows.
    For 8x16, OAM tile LSB determines CHR bank, not PPUCTRL sprite bit.
    """
    if (type(tile) is not int or not 0 <= tile <= 255 or
        type(x) is not int or not 0 <= x < 8 or
        type(height) is not int or height not in (8, 16) or
        type(y) is not int or not 0 <= y < height or
        type(hflip) is not bool or type(vflip) is not bool or
        type(sprite_table_high) is not bool or
        not isinstance(low, (bytes, bytearray)) or
        not isinstance(high, (bytes, bytearray)) or
        len(low) != height or len(high) != height):
        raise SpriteFlipError('Untrusted sprite or CHR pattern shape')
    line = height - y - 1 if vflip else y
    bit = x if hflip else 7-x
    value = ((low[line] >> bit) & 1) | (((high[line] >> bit) & 1) << 1)
    if height == 16:
        bank = (tile & 1) << 12
        pattern_num = (tile & ~1) | (line >> 3)
    else:
        bank = 4096 if sprite_table_high else 0
        pattern_num = tile
    address = bank + pattern_num*16 + (line & 7)
    return value, address


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pinned_ppu_cpp', type=Path)
    args = parser.parse_args()
    verify_source(args.pinned_ppu_cpp.read_bytes())
    print('STAGE132_PINNED_SPRITE_FLIP_SOURCE_PASS '
          'horizontal=bit_reverse vertical=reverse_row '
          'sprite_8x16=bank_tile_pair source_only=yes '
          'native_flip_pixels_proven=no '
          'original_game_sprite_flips_proven=no')
