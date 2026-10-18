# Stage128 — pinned FCEUX sprite compositing source contract

## Native sprite proof is not yet claimed

Stage127 established the four-quadrant universal background color
from actual FCEUX XBuf output on generated Mapper-4 ROMs. It did not
enable or instrument the NES sprite renderer.

Stage128 inspects the **original, pinned FCEUX source file**
`src/ppu.cpp` at revision
`8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8` before applying
any PPU research patches. The new auditor anchors the real `newppu`
pixel-rendering loop and checks that the critical source expressions
occur exactly once, in the correct order and within one small
compositor block.

It explicitly distinguishes these behaviors:

- A sprite pixel with both CHR planes zero is ignored.
- A sprite marked *behind the background* is visible through a
  background CHR pixel whose low two bits are zero, even when the
  background attribute palette bits are nonzero.
- If the background's CHR low two bits are nonzero, a sprite marked
  behind it loses the pixel, but the sprite-0 hit can still be set.
- Sprite-0 hit additionally requires sprite OAM index zero, a
  nontransparent sprite pixel and screen X less than 255.
- Visible sprite palette indices begin at `0x10`, plus the
  two-bit sprite pattern and the sprite's palette selector.
- The resulting palette lookup is eventually written to XBuf through
  FCEUX's `PaletteAdjustPixel`.

The audit scopes to the **newppu compositor** because the same
`PPU_status |= 0x40` expression also appears in older renderer
paths. It does not infer newppu behavior from unrelated C++ lines.

The independent Python model exercises 32 combinations of background
pattern 0..3, sprite pattern 0..3 and priority front/behind, along
with sprite-0 hit, clipping and deliberately malformed parameters.
Every source anchor has a missing/duplicated/reordered negative test.

## Verification

```bash
python -m unittest discover -s tests -p 'test_fceux_stage128_sprite_compositor.py' -v
```

The pinned-FCEUX CI job separately calls:

```bash
python tools/audit_fceux_stage128_sprite_compositor.py \
  "$FCEUX/src/ppu.cpp"
```

Only a successful pinned build confirms the exact upstream source.
This is a **source-level contract and an independent model**, not
an actual generated OAM sprite seen in XBuf. Future native experiments
must populate controlled OAM entries and sprite CHR, assert sprite
priority and sprite-0 status on the real FCEUX renderer, and compare
the actual framebuffer and negative controls.

No original Vice: Project Doom resources are published or validated
by Stage128, and no Nintendo Switch sprite renderer is claimed.
