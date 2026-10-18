# Stage 86 — frame labels, observed CPU-cycle intervals and PPU timing limits

## Problem

The FCEUX video trace records two independently useful observations:
a frame label from `emu.framecount()`, and, when available, a CPU-cycle
counter from `debugger.getcyclescount()`. The stage85 checks proved only
the order of **recorded callbacks**, not the exact position of a PPU
frame boundary. In particular, the difference between the last
registered event in frame N and the first registered event in N+1
must not be reported as the elapsed duration of frame N.

The frame labels can jump without a logging failure: many frames may
contain no selected PPU/MMC3 register events. The absence of an event
is not proof that the emulator skipped a displayed frame.

## Diagnostics: `tools/analyze_ppu_cycle_trace.py`

The diagnostic `summarize()` result now has
`frame_boundary_observations`, one record for each transition between
**consecutive logged event-frame groups**. Each record contains:

- Previous/current event frame labels and their difference
- Last CPU-cycle value associated with the prior event frame
- First CPU-cycle value associated with the next event frame
- Difference between those two **logged event timestamps**, but only
  when frame labels increase and the CPU-cycle counter does not decrease
- Number of intermediate frame labels with no logged event
- A flag when the counter decreases at the transition

`physical_frame_start_cycle` and
`physical_frame_duration_cycles` are always `null`. The summary also
reports `frame_start_cycle_proven=false` and
`ppu_scanline_position_proven=false`.

An equal timestamp yields an observed interval of zero and is
**not** classified as an error. A decreasing counter or reversed event
frame label makes the cross-group interval unavailable (`null`).
A jump from frame 3 to frame 7 contributes three frame labels with no
logged register event, **not three proven missed frames**.

This report is diagnostic only and can describe an unverified trace.
It must never be used to infer NES raster scanlines, VBlank,
frame-start timing or 1:1 CPU-cycle-to-PPU-dot correlation.

## Strict session verification

`tools/verify_ppu_capture_session.py` already enforces stage79–85
event sequence, session continuity, event checksums and CPU-cycle
ordering. Stage86 adds a logically independent causal check:

> A snapshot saved by the frame-N `emu.registerafter` callback may
> not contain an event labeled with a future frame number in the
> event-log prefix it commits.

Because event frames are nondecreasing, this can be tested from the
last row included in the snapshot's `logged_register_writes` count.
An earlier snapshot whose prefix includes an event marked frame N+1
is rejected even when both TSV files, the snapshot's prefix checksums
and all finalized digests have been recalculated to agree.

Successful verification reports
`snapshot_event_frame_order_verified=true` while explicitly retaining
`physical_frame_boundaries_proven=false`. This is a logical
synchronization test against the observed emulator labels, not
verification of the actual NES PPU raster.

## Tests and verification

- Six synthetic `summarize()` scenarios were executed locally on an
  isolated copy of the actual production function; **6/6 passed**.
- Six new unit tests in `tests/test_ppu_cycle_trace.py` check
  adjacent frames, gaps, equal timestamps, counter regressions,
  out-of-order labels, and empty/single-frame logs.
- Two new tests in `tests/test_ppu_capture_session.py` check that
  future-labeled events in an earlier snapshot are rejected despite
  recomputed hashes, and that a verified frame-label order does not
  imply measured PPU frame boundaries.
- The cycle diagnostic test suite now has a dedicated CI step; the
  capture-session suite is already included in CI.

**Verification boundary:** the full updated GitHub test suite has
not yet executed on an allocated runner. The targeted local tests
above do not imply FCEUX runtime testing or original-game accuracy.

No original ROM, frame dumps, game geometry or Nintendo Switch NRO
are stored in the branch.
