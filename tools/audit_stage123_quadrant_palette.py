#!/usr/bin/env python3
"""Stage123 synthetic NES attribute quadrants; not a native pixel proof.

A separate preflight for four distinct 2x2-tile quadrants. The FCEUX
Stage119-122 native chain must remain independent; this does not observe
PPU RAM, original game sprites, final XBuf or actual palette fetches.
"""

ATTRIBUTE_BYTE = 0xE4
PALETTE_RAM = (0x0F, 0x16, 0x27, 0x30,
               0x0F, 0x11, 0x21, 0x31,
               0x0F, 0x12, 0x22, 0x32,
               0x0F, 0x13, 0x23, 0x33)


class QuadrantEvidenceError(ValueError):
    pass


def source(tile_x, tile_y, page=0):
    if (type(tile_x) is not int or not 0 <= tile_x < 32 or
            type(tile_y) is not int or not 0 <= tile_y < 30 or
            type(page) is not int or not 0 <= page < 4):
        raise QuadrantEvidenceError("Out-of-range synthetic nametable coordinates")
    return 0x2000 + (page << 10) + (tile_y << 5) + tile_x


def attr_addr(nt):
    if type(nt) is not int or not 0x2000 <= nt < 0x3000:
        raise QuadrantEvidenceError("Not a physical PPU nametable source")
    return 0x23C0 + (nt & 0x0C00) + ((nt & 0x0380) >> 4) + ((nt & 0x001C) >> 2)


def attr_shift(nt):
    if type(nt) is not int or not 0x2000 <= nt < 0x3000:
        raise QuadrantEvidenceError("Not a nametable source")
    return 4 * ((nt >> 6) & 1) + 2 * ((nt >> 1) & 1)


def decode(nt, attribute_byte, chr_pattern, palette=PALETTE_RAM):
    if (type(attribute_byte) is not int or not 0 <= attribute_byte <= 255 or
            type(chr_pattern) is not int or not 1 <= chr_pattern <= 3 or
            len(palette) != 16 or any(type(c) is not int or not 0 <= c <= 63
                                      for c in palette)):
        raise QuadrantEvidenceError("Invalid synthetic attribute/pixel/palette")
    shift = attr_shift(nt)
    group = (attribute_byte >> shift) & 3
    index = 4 * group + chr_pattern
    return dict(source=nt, attribute_address=attr_addr(nt),
                shift=shift, group=group, pixel_index=index,
                palette_color=palette[index])


def audit_four_quadrants(attribute_byte=ATTRIBUTE_BYTE, palette=PALETTE_RAM):
    samples = [decode(source(x, y), attribute_byte, 3, palette)
               for x, y in ((0, 0), (2, 0), (0, 2), (2, 2))]
    if ([p["group"] for p in samples] != [0, 1, 2, 3] or
            [p["pixel_index"] for p in samples] != [3, 7, 11, 15] or
            len({p["palette_color"] for p in samples}) != 4 or
            len({p["attribute_address"] for p in samples}) != 1):
        raise QuadrantEvidenceError("Four independent palette groups not witnessed")
    return dict(palette_groups=4, distinct_colors=4,
                observed_pixel_indices=[3, 7, 11, 15],
                original_game_palette_proven=False,
                native_fceux_palette_proven=False)


if __name__ == "__main__":
    audit_four_quadrants()
    print("STAGE123_SYNTHETIC_QUADRANT_PREFLIGHT "
          "groups=4 indices=3,7,11,15 distinct_palette_colors=4 "
          "native_fceux_proven=no original_game_palette_proven=no")
