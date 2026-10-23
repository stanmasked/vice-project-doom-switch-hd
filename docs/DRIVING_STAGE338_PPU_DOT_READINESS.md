# Stage 338 — PPU raster-dot reference model and evidence readiness gate

Stage 337 independently replayed the CPU-visible `$2000/$2001/$2002/$2005/$2006`
register sequence, including the shared write toggle. That is **not** an
observation of the PPU's internal `v` during rendering. Stage 338 separates
hardware-rule regression tests from the still-missing original-source dot
witness. No gameplay, camera, rendering or physics code is changed.

## New tools

- `tools/ppu_dot_scroll_model.py`: ROM-free reference model for `v`, `t`, `x`,
  `w`, PPUCTRL and PPUMASK with the standard NTSC visible/pre-render
  scanline-dot Loopy address transitions. The model includes coarse-X wrap,
  fine/coarse-Y increment (including Y=29 and Y=31 cases), horizontal `t→v`
  reload at dot 257, and vertical `t→v` reload on pre-render dots 280–304.
  The model is deterministic and does **not** claim to be an original-emulator
  `v` observation, a cycle-exact bus emulator, or a renderer.
- `tools/audit_private_ppu_dot_readiness.py`: private-input preflight for the
  already sealed Stage335 CPU-event trace. Verifies byte-for-byte source file
  identity against an owner-private SHA-256 and checks 261 source frames,
  21,398 event rows, and the complete Stage335 register event baseline.
  It explicitly reports **no authenticated internal PPU `v`/dot witness**,
  even though CPU cycles are captured. Rejects synthetic/unsupported dot
  fields rather than mistaking them for source PPU observations.
- `tests/test_stage338_ppu_dot_model.py`: **24 source-free tests** for CPU
  register state, hardware raster transitions, absent rendering, invalid
  values, source baseline rejection and unsupported witness claims.
- `docs/stage338_public_aggregate.json`: redacted source preflight. No raw
  source byte values, instruction sites, source paths, source checksums, ROMs,
  FM2 recordings or original image data are committed.

## What was confirmed

The owner-private Stage335 original-source file was rechecked against its
private SHA-256 manifest. The source readiness preflight passed the Stage335
counts: 261 frames and 21,398 CPU events, including 10,172 `$2002` status
reads, 844 `$2000` writes, 506 `$2001` writes, 1,010 `$2005` writes and
6,096 `$2006` writes. The source file does **not** contain direct PPU
scanline/dot coordinates or the internal `v` register at rendering dots.

Synthetic tests for the independent model passed (24/24). This is a model
validation **only**, not a source claim that the original game drew a given
road position or that the measured CPU cycles uniquely determine PPU dots.

## Owner-private command

After verifying the original Stage335 capture manifest, use its SHA-256
without exposing the value to GitHub:

```sh
python tools/audit_private_ppu_dot_readiness.py \
  --input /private/Stage335/stage335_ppu_latch_ram0d_events.tsv \
  --source-sha256 "$EXPECTED_PRIVATE_SOURCE_SHA256" \
  --require-stage335-baseline \
  --output /private/Stage338/stage338-readiness.json
```

The output is a sanitized gap report. The presence of a true PPU-dot witness
requires **a separate source capture and independent validation**; this
command cannot create one from CPU events.

## Evidence still required

Next, obtain a vetted NTSC PPU internal state or rendering-fetch trace that
records the actual scanline, dot and relevant `v` values for a bounded
original-source window. Authenticate it against the ROM/FM2 and frame order;
then compare these observations with this model and the existing 41-slot RGB
road evidence, accounting for odd-frame behavior, PPU `$2007` increments,
CPU writes between hardware transitions and emulator event ordering. Until
such a witness or separately validated renderer comparison exists, **effective
raster scroll, road geometry, camera speed and collision remain unproven**.

Hardware behavior reference: https://www.nesdev.org/wiki/PPU_scrolling
