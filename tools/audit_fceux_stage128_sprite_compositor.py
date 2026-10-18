#!/usr/bin/env python3
"""Stage128 source-anchored newppu sprite/background priority audit.

This proves only the pinned C++ source contract. Pixel compositing tests
are an independent pure-Python reference, NOT a native ROM result.
"""
import argparse
from pathlib import Path


class SpriteSourceError(ValueError):
    pass


ANCHORS = (
    "const bool renderspritenow = SpriteON && (xt > 0 || SpriteLeft8);",
    "const bool renderbgnow = ScreenON && (xt > 0 || BGLeft8);",
    "if (renderbgnow) {",
    "pixel = ((pt[0] >> (7 - bgpx)) & 1)",
    "if (spixel == 0) continue;",
    "if (oam[6] == 0 && (pixel & 3) != 0 &&",
    "rasterpos < 255) {",
    "PPU_status |= 0x40;",
    "if (oam[2] & 0x20) {",
    "if ((pixel & 3) != 0) continue;",
    "spixel |= (oam[2] & 3) << 2;",
    "pixelcolor = READPALNOGS(0x10 + spixel);",
    "*ptr = PaletteAdjustPixel(pixelcolor);",
)


def verify_sprite_source(source):
    if isinstance(source, bytes):
        source = source.decode("latin1")
    if not isinstance(source, str):
        raise SpriteSourceError("Pinned FCEUX ppu.cpp expected")
    # Scope to the real newppu pixel loop: older renderer paths also
    # write PPU_status sprite0 and must not count as newppu evidence.
    start, end = ANCHORS[0], ANCHORS[-1]
    if source.count(start) != 1 or source.count(end) != 1:
        raise SpriteSourceError("Missing or ambiguous newppu compositor")
    segment = source[source.index(start):source.index(end) + len(end)]
    indices = []
    for anchor in ANCHORS:
        if segment.count(anchor) != 1:
            raise SpriteSourceError("Missing/ambiguous newppu sprite step: " + anchor)
        indices.append(segment.index(anchor))
    if indices != sorted(indices):
        raise SpriteSourceError("Sprite/bg priority source order changed")
    if len(segment) > 11000:
        raise SpriteSourceError("Sprite compositor anchors too far apart")
    return {"priority_source_verified": True, "sprite_hit_bg_nonzero": True,
            "behind_bg_blocked_when_bg_nonzero": True,
            "transparent_sprite_skipped": True,
            "actual_game_sprites_proven": False,
            "native_sprite_pixels_proven": False}


def compose(bg_pattern, bg_group, sprite_pattern, sprite_group,
            *, behind=False, sprite_enabled=True, bg_enabled=True,
            sprite_zero=True, x=64):
    for v in (bg_pattern, bg_group, sprite_pattern, sprite_group, x):
        if type(v) is not int:
            raise SpriteSourceError("Integer pixel fields required")
    if (bg_pattern not in range(4) or bg_group not in range(4) or
            sprite_pattern not in range(4) or sprite_group not in range(4) or
            not 0 <= x <= 255 or any(type(b) is not bool for b in
            (behind, sprite_enabled, bg_enabled, sprite_zero))):
        raise SpriteSourceError("Out-of-range sprite/background pixel")
    effective_bg = bg_pattern if bg_enabled else 0
    bg_index = effective_bg + 4 * (bg_group if bg_enabled else 0)
    if not sprite_enabled or sprite_pattern == 0:
        return {"palette_index": bg_index, "sprite_visible": False,
                "sprite0_hit": False}
    hit = sprite_zero and effective_bg != 0 and x < 255
    visible = not (behind and effective_bg != 0)
    return {"palette_index": (0x10 + sprite_pattern + 4 * sprite_group)
            if visible else bg_index,
            "sprite_visible": visible, "sprite0_hit": hit}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("pinned_ppu_cpp", type=Path)
    args = cli.parse_args()
    verify_sprite_source(args.pinned_ppu_cpp.read_bytes())
    print("STAGE128_PINNED_NEWPPU_SPRITE_COMPOSITOR_SOURCE_PASS "
          "priority=behind_bg transparency=zero sprite0_hit=nonzero_bg "
          "source_only=yes native_sprite_pixels_proven=no "
          "original_game_sprites_proven=no")


if __name__ == "__main__":
    main()
