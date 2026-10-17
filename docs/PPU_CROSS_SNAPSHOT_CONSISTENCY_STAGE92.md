# Stage 92 — verified cross-snapshot screen consistency

## Purpose and evidence limits

Stage91 measured 8x8 screen-cell matches against **assumed zero-scroll
static background hypotheses**, while Stage90 counted CPU-side register
callbacks. Neither could show whether apparent graphics persist between
successive verified FCEUX screen captures. Stage92 adds an explicitly
**screen-coordinate-only** comparison:

`tools/audit_ppu_cross_snapshot_consistency.py`

The analysis joins the Stage91 evidence summary with Stage88 verified memory
deltas for each pair of **successive saved snapshots**. It never treats a gap
between captures as fully observed original frames, and never infers camera
movement, world tiles, CHR raster mapping, or NES scanline timing.

## Private local execution

```bash
python3 tools/audit_ppu_cross_snapshot_consistency.py \
  private/ppu_capture_session.meta.txt \
  --require-cycle --require-screen-pair \
  --out private/cross_snapshot_consistency_stage92.json
```

`--require-cycle` requires a valid logged CPU clock; it **does not** prove
VBlank/scanline timing. `--require-screen-pair` rejects a session in which
no two consecutively saved snapshots both have verified screen images.
Without these flags, missing observations remain explicit instead of being
invented. All original ROM/graphics captures and even derived numerical
reports from the owner's game should stay private, off public GitHub.

## 8x8 cell classification

Every saved 256x240 screen contains 960 nonoverlapping screen-space cells.
For two verified screen planes from consecutive *saved snapshots*, compare
palette indices at identical screen coordinates; indices 254 mean unknown.
Counts are mutually exclusive:

| Report class | Meaning |
| --- | --- |
| `fully_known_identical` | All 64 positions observed and equal |
| `fully_known_changed` | All 64 positions observed, at least one differs |
| `partially_unknown` | One or more pixels unknown in either capture; the entire cell is withheld |
| `unassessed_missing_reference` | One or both images absent; no screen comparison is attempted |

A 100% identical screen-plane result would establish **only equality of
screen-coordinate palette indices at two sampled moments**. Stationary
background, an unchanged HUD, sprites, animation, a scrolling scene that
happens to look similar, and a blank backdrop can all produce identical
pixels. The report cannot claim the same world tile occupied those pixels.

For every snapshot pair the report also includes:

- Exact captured frame-label distance and number of intermediate frame labels
  **without saved snapshots**.
- Verified Stage90 register-event counts between snapshot checkpoints,
  including CHR, PPUSCROLL and PPUADDR activity; their raster timing is unknown.
- Verified Stage88 aggregate byte differences in PPU/CHR/nametable/palette
  memory; their causal relationship to visible pixels is unknown.
- Previous and current Stage91 static-match candidate counts, **without**
  inventing a cell-by-cell correspondence or camera path.

All `level_geometry_reconstruction_ready_cells` remain **zero**.
This is a diagnostic and coverage gate for further private capture work, not
an HD background exporter or a reconstruction of level one.

## ROM-free synthetic tests and CI

```bash
python3 -m unittest discover -s tests -p 'test_ppu_cross_snapshot_consistency.py' -v
```

Tests require no original ROM or game graphics. They cover exact and changed
screen comparisons, deliberately unknown pixels, corrupt inputs, one-sided
missing references, checksum tampering, real session/event-prefix validation,
nonconsecutive frame labels, and missing optional CPU-clock evidence.
CI reruns the tests independently after full Python discovery.

## Next gate

Authenticate private first-level captures, sample raster-aligned PPU events,
separate sprite and background contributions, and only then test independently
verified camera displacement with nametable/CHR continuity. Do not switch on
HD asset replacement or assert authentic level geometry from these reports.
