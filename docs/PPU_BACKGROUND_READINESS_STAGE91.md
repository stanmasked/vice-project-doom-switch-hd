# Stage 91 — conservative background-reconstruction readiness

Stage90 supplies verified **CPU register callback windows**, not PPU raster
timing. Stage89 supplies **zero-scroll static background candidates** compared
to verified FCEUX screen palette-index references, not authentic level
geometry. Stage91 connects these two bodies of evidence without promoting
either to a verified first-level map.

## Run only on privately captured and verified inputs

```bash
python3 tools/audit_ppu_background_readiness.py \
  private/ppu_capture_session.meta.txt \
  --require-cycle --require-screen \
  --out private/background_readiness_stage91.json
```

The input is the complete local session manifest already accepted by
`verify_ppu_capture_session.verify()`. Verification covers ordered event-log
checkpoints, all required snapshot and screen checksums, and the whole session.
A failed or altered session is rejected before its raster data are inspected.
The optional cycle requirement proves CPU log ordering only, never a PPU
scanline or physical frame boundary.

**Keep all original ROM, PPU snapshots, screenshots, and derived reports
private.** Do not commit captures, numerical results from the commercial game,
tile IDs, bank values, or images to this public repository. This tool reports
only synthetic-safe, aggregate counts, with no per-cell coordinates or pixels.

## Classification

Each saved screen contains 960 local **8×8 screen cells** (32×30). These are
comparison bins, **not NES nametable tiles** or world-space level coordinates.
For each frame with a verified saved palette-index reference, test exactly
the Stage89 candidate family: four nametables, both PPU pattern bases only
when the snapshot PPUCTRL bit is unknown, static zero scroll, no sprites.
The per-cell classes are mutually exclusive:

| Class | Operational meaning |
| --- | --- |
| `unanimous_static_match` | Every tested static candidate matches all 64 observed pixel indices |
| `hypothesis_dependent_static_match` | Some, but not all, tested candidates exactly match all 64 indices |
| `no_exact_static_match` | No tested candidate exactly matches all 64 indices |
| `incomplete_reference` | At least one of 64 reference indices is unknown (254) |
| `unassessed_no_reference` | The verified snapshot has no saved rendered-screen reference |

Missing pixels are never treated as matching. A partial cell is excluded
entirely, rather than allowing an artificially perfect match from sparse
coverage. For each verified snapshot window, the report also lists aggregate
observed CHR, PPUADDR and PPUSCROLL activity and separately retains
`visible_scroll_proven=false`, `scanline_chr_mapping_proven=false`,
and `event_to_raster_alignment_proven=false`.

An all-candidate exact match is only **candidate consensus for a particular
unscrolled static model**. It does not establish that the matching pixels
were background rather than sprites or effects, that the snapshot's CHR
configuration was active on those scanlines, or that the frame depicts the
game's first level. All `reconstruction_ready_cells` are therefore **zero**
until independent capture identity, raster timing, background/sprite
segmentation, and cross-frame world continuity can be demonstrated.

## Synthetic verification

```bash
python3 -m unittest discover -s tests -p 'test_ppu_background_readiness.py' -v
```

Regression cases cover unanimous and hypothesis-dependent matches, wholly
incompatible cells, unknown pixels, malformed inputs, absent references,
a verified synthetic screen with actual event-window binding, checksum
tampering, and the optional cycle requirement. Tests contain no commercial
game content.

## Next research gate

1. Capture and locally authenticate first-level identity without publishing
   the ROM or its original graphics.
2. Establish PPU scanline/frame alignment independently of register callbacks
   before using CHR or scroll events to interpret rendered pixels.
3. Separate sprites/effects from background and validate cross-frame camera
   displacement and nametable continuity.
4. Only after these gates, propose background art/layout candidates with
   precise provenance and manual review.

This stage changes analysis tooling only; it does not enable HD replacement
or claim Switch gameplay reconstruction.
