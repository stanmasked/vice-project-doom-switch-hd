# Stage132 — pinned FCEUX sprite reflection source contract

## Evidence scope

Stage131 passed pinned native FCEUX run 39085959483: five overlapping OAM sprite scenarios, 40 observed final XBuf pixels, and both negative controls. Stage132 is a separate source-level audit and reference-model check for horizontal and vertical sprite reflection. It is **not** yet proof of actual reflected sprite pixels in the emulator.

In pinned upstream FCEUX `ppu.cpp` revision `8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8`, the sprite-fetch path uses `oam[2] & 0x80` to reverse the source row. Horizontal flip sets OAM bit `0x40`, which causes the PPU source path **not** to run `bitrevlut`; the raster loop subsequently consumes the low bits of both CHR planes. Thus the reference's source bit is `7-x` without H-flip, or `x` with H-flip.

For an 8×8 sprite, the pattern table follows the PPUCTRL `SpAdrHI` setting. For an 8×16 sprite, the CHR bank is selected by the low bit of the sprite tile ID, and the effective (possibly reflected) row chooses the top or bottom tile of an adjacent pair. The independent reference returns both the exact low-plane CHR address and the two-bit pattern value.

## Verification and mutation controls

`tools/audit_stage132_sprite_flips.py` checks two **different source regions** — CHR-plane fetch and raster pixel consumption — requiring exact operation anchors once and in the correct order. Removing, duplicating or reordering anchors fails closed. The reference-model suite covers six test methods: all four flip modes on asymmetric 8×8 CHR, nonzero dual-plane patterns, 8×16 bank/tile-pair selection, and malformed-input controls.

```bash
python -m unittest discover -s tests -p 'test_fceux_stage132_sprite_flips.py' -v
python tools/audit_stage132_sprite_flips.py /path/to/pinned/fceux/src/ppu.cpp
```

Pinned GitHub Actions runs the source audit on the exact upstream `ppu.cpp` before installing any tracing hooks; its other CI group runs the six regression methods.

The success marker is `STAGE132_PINNED_SPRITE_FLIP_SOURCE_PASS` and explicitly reports `native_flip_pixels_proven=no`. Its result is not interchangeable with the native Stage131 marker.

## Next boundary

A stronger native proof needs a synthetic Mapper-4 ROM with deliberately asymmetric CHR rows and columns, four flip-bit variations in OAM, a raster witness of the actually fetched row and pattern bits, and corresponding final XBuf pixels. Negative controls must reject forged flip flags and mismatched CHR data.

No original *Vice: Project Doom* image data or ROMs enter public GitHub. Original-game sprite flips and a functioning Nintendo Switch HD renderer remain unproven.
