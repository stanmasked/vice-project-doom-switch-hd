# Stage 93 — CPU callback sequence versus screen-change evidence

## What is now measured

Stage92 compared identical **screen coordinates** across two *saved* FCEUX
snapshots. Stage93 adds ordered families of the **verified CPU callback log**
between those exact saved snapshot event-prefix checkpoints.

Tool: `tools/audit_ppu_temporal_evidence.py`.

Families are `chr_context` (MMC3 selector and CHR-register data writes or
data with unknown selector), `scroll_address` ($2005/$2006),
`display_control` ($2000/$2001 and MMC3 mirroring control),
`ppu_data` ($2007), `status_latch` ($2002 read markers), and `other`.
MMC3 selector writes are flagged conservatively: they may select a PRG
register and need not change actual CHR rendering.

Output measures counts, distinct callback frame labels, the number of
collapsed **background-family** transitions and whether event families are
observed once or interleaved. The only ordering certified here is committed
CPU callback sequence. A callback frame label is not a measured physical
PPU frame boundary or a scanline. An optional CPU-cycle log still does not
supply scanline position.

The prior snapshot's selector carries across checkpoint windows during
private analysis. Actual selector IDs, CHR bank data, PPU values, raw palette
indices, pixels, and per-cell positions are **never emitted**. Reports
include Stage92 counts of identical and changed 8×8 screen cells only.

## Local/private command

```bash
python3 tools/audit_ppu_temporal_evidence.py \
  private/ppu_capture_session.meta.txt \
  --require-cycle --require-screen-pair \
  --out private/ppu_temporal_stage93.json
```

Inputs must satisfy the existing whole-session integrity verification and
the Stage90/91/92 audit gates. Private capture bytes and game-derived
numeric reports must stay outside the public repository.

A pair is labeled as either lacking a comparable reference, having no
fully known cell, or showing one of four **co-occurrence** classes:
observed screen change with/without selected CPU callbacks or no observed
change with/without those callbacks. The labels **never assert that the
callbacks caused pixels to change**. Equally, no selected callbacks does
not mean the picture must be static: sprites, DMA, animation, VRAM changes,
off-screen execution and unmeasured raster state remain possible.

`events_labeled_at_or_before_previous_snapshot` measures ambiguous
callback-frame labeling across committed snapshot boundaries rather than
treating labels as accurate VBlank boundaries. Saved snapshots may omit
intervening frames even when callback logging was complete.

## How this advances reconstruction

The diagnostic now identifies which **private capture windows** deserve a
better raster trace because they have mixed CHR/scroll/control/PPU-data
activity, unknown scroll latch state, incomplete scroll writes, or a
screen/callback co-occurrence. This supports selection of next
observations, not generation of world coordinates or HD assets.

All `level_geometry_reconstruction_ready_cells` are zero. We still need
independent first-level ROM provenance, PPU-visible scanline-aligned
scroll/CHR observations, sprite-background separation and verified
world-space continuity. Avoid exporting original graphics, and leave
HD substitution disabled.

## Tests

```bash
python3 -m unittest discover -s tests -p 'test_ppu_temporal_evidence.py' -v
```

Synthetic tests cover MMC3 selector carryover and PRG exclusions,
mirrored PPU ports, status markers, PPU data/display controls,
interleaving, ambiguous callback frame labels, missing or identical
screen pairs, changed pairs, tampered verified event logs and optional
CPU-cycle evidence. No commercial ROM or capture is used in CI.
