#!/usr/bin/env python3
"""Stage130 pinned-newppu two-OAM-sprite priority-order *model only*.

Independent no-ROM preflight, not a native FCEUX dual-sprite proof.
Sprite selection occurs before sprite/background priority resolution.
"""
from dataclasses import dataclass


class OverlapError(ValueError):
    pass


ANCHORS = (
    "for (int s = 0; s < oamcount; s++) {",
    "if (havepixel) continue;",
    "if (spixel == 0) continue;",
    "if (oam[6] == 0 && (pixel & 3) != 0 &&",
    "rasterpos < 255) {",
    "PPU_status |= 0x40;",
    "havepixel = true;",
    "if (oam[2] & 0x20) {",
    "if ((pixel & 3) != 0) continue;",
    "spixel |= (oam[2] & 3) << 2;",
    "pixelcolor = READPALNOGS(0x10 + spixel);",
)


def verify_source(source):
    if isinstance(source, bytes):
        source = source.decode("latin1")
    if not isinstance(source, str):
        raise OverlapError("Missing pinned newppu C++ source")
    start = ANCHORS[0]
    end = "*ptr = PaletteAdjustPixel(pixelcolor);"
    if source.count(start) != 1 or source.count(end) != 1:
        raise OverlapError("Ambiguous native sprite loop")
    region = source[source.index(start):source.index(end)+len(end)]
    locations = []
    for anchor in ANCHORS:
        if region.count(anchor) != 1:
            raise OverlapError("Ambiguous compositor order: " + anchor)
        locations.append(region.index(anchor))
    if locations != sorted(locations) or len(region) > 8000:
        raise OverlapError("Sprite priority/selection source order changed")
    return {"two_sprite_source_order_verified": True,
            "native_two_sprite_pixels_proven": False,
            "original_game_sprite_proven": False}


@dataclass(frozen=True)
class Sprite:
    oam_index: int
    pattern: int
    palette: int
    behind: bool = False


def compose(bg_pattern, bg_group, sprites, *, x=64, sprite_enabled=True):
    if (type(bg_pattern) is not int or bg_pattern not in range(4) or
        type(bg_group) is not int or bg_group not in range(4) or
        type(x) is not int or not 0 <= x < 256 or
        type(sprite_enabled) is not bool or
        not isinstance(sprites, (list, tuple)) or len(sprites) != 2):
        raise OverlapError("Invalid sprite compositor scenario")
    for i, sp in enumerate(sprites):
        if (not isinstance(sp, Sprite) or type(sp.oam_index) is not int or
            sp.oam_index != i or type(sp.pattern) is not int or
            sp.pattern not in range(4) or type(sp.palette) is not int or
            sp.palette not in range(4) or type(sp.behind) is not bool):
            raise OverlapError("Sprite OAM ordering or CHR inputs invalid")
    bg_color = 0x30 + bg_group if bg_pattern else 0x0F
    color = bg_color
    sprite0_hit = False
    claimed = None
    drawn = None
    if sprite_enabled:
        for sp in sprites:
            if sp.pattern == 0:
                continue
            if sp.oam_index == 0 and bg_pattern != 0 and x < 255:
                sprite0_hit = True
            claimed = sp.oam_index  # set before behind-background check
            if not (sp.behind and bg_pattern != 0):
                color = (0x2A, 0x38, 0x39, 0x3A)[sp.palette]
                drawn = sp.oam_index
            break                   # havepixel blocks later sprites
    return {"xbuf": 0x80 | color, "claimed_oam": claimed,
            "drawn_oam": drawn, "sprite0_hit": sprite0_hit,
            "native_two_sprite_pixels_proven": False}


if __name__ == "__main__":
    a = compose(3, 0, [Sprite(0, 3, 0), Sprite(1, 3, 1)])
    assert a["xbuf"] == 170
    print("STAGE130_TWO_SPRITE_ORDER_MODEL_PASS "
          "source_only=no independent_model=yes "
          "native_two_sprite_pixels_proven=no original_game_sprite_proven=no")
