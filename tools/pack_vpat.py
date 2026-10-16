#!/usr/bin/env python3
"""Pack a user-authored RGBA PNG sheet as a validated VPAT v1 sprite atlas.

Frames are row-major non-overlapping rectangular cells. Original game assets
are neither required nor bundled. Keep any proprietary source art private.
"""
import argparse
import re
import struct
import zlib
from pathlib import Path
from PIL import Image

MAX_SIDE = 1024

def pack_image(path, frame_width, frame_height, frame_count):
    with Image.open(path) as source:
        if source.format != 'PNG':
            raise ValueError('Source must be PNG')
        width, height = source.size
        if (not 0 < width <= MAX_SIDE or not 0 < height <= MAX_SIDE
            or not 0 < frame_width <= width or not 0 < frame_height <= height
            or width % frame_width or height % frame_height):
            raise ValueError('Invalid atlas/frame dimensions (must tile, max 1024 per side)')
        if not 0 < frame_count <= (width // frame_width) * (height // frame_height):
            raise ValueError('Invalid frame count')
        pixels = source.convert('RGBA').tobytes()
    header = b'VPAT' + struct.pack('<7H', 1, width, height, frame_width,
                                    frame_height, frame_count, 0)
    return header + struct.pack('<I', zlib.crc32(pixels) & 0xffffffff) + pixels


def cpp_header(blob, namespace='vpd_art', symbol='kAtlasBlob'):
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z_0-9]*', namespace) or not re.fullmatch(
            r'[a-zA-Z_][a-zA-Z_0-9]*', symbol):
        raise ValueError('Invalid C++ namespace or symbol')
    rows = ['    ' + ', '.join('0x%02x' % b for b in blob[i:i+20]) + ','
            for i in range(0, len(blob), 20)]
    return ('#pragma once\n#include <cstddef>\nnamespace ' + namespace +
            ' {\ninline constexpr unsigned char ' + symbol + '[] = {\n' +
            '\n'.join(rows) + '\n};\ninline constexpr std::size_t kAtlasBytes=' +
            'sizeof(' + symbol + ');\n}\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('png', type=Path)
    p.add_argument('--frame-width', type=int, required=True)
    p.add_argument('--frame-height', type=int, required=True)
    p.add_argument('--frames', type=int, required=True)
    p.add_argument('--header', type=Path)
    p.add_argument('--binary', type=Path)
    p.add_argument('--namespace', default='vpd_art')
    p.add_argument('--symbol', default='kAtlasBlob')
    args = p.parse_args()
    if args.header is None and args.binary is None:
        p.error('At least one output (--header or --binary) is required')
    blob = pack_image(args.png, args.frame_width, args.frame_height, args.frames)
    if args.header:
        args.header.parent.mkdir(parents=True, exist_ok=True)
        args.header.write_text(cpp_header(blob, args.namespace, args.symbol), encoding='utf8')
    if args.binary:
        args.binary.parent.mkdir(parents=True, exist_ok=True)
        args.binary.write_bytes(blob)
    print(f'VPAT v1: {len(blob)-22} pixel bytes, {args.frames} frames, '
          f'CRC32={struct.unpack_from("<I",blob,18)[0]:08x}')


if __name__ == '__main__':
    main()
