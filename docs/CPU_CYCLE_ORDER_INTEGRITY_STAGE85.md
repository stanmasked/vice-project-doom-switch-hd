# Stage 85 — CPU-cycle ordering, reset ambiguity and evidence gating

## Finding

A valid pair of PPU event TSV logs can have matching row counts,
matching addresses and valid Adler-32 digests, while its CPU-cycle
counter **decreases** between consecutive callbacks. That decrease
might result from an explicit FCEUX debugger counter reset, a restart,
a corrupted event stream, or another discontinuity. The trace alone
does not identify which explanation is correct. Counting such a
decrease as a proven reset would be unsupported.

Repeated identical cycle values are different: more than one callback
can report the same sampled counter. They are not independently
evidence of corruption, but must be accounted for.

## Recorder: `tools/capture_fceux_ppu.lua`

The exact production event callback now tracks:

- `cycle_regressions`: all strict decreases between adjacent recorded
  CPU-cycle values
- `cycle_regressions_same_frame`: decreases when both events share a
  reported frame number
- `cycle_regressions_between_frames`: decreases across frame labels
- `cycle_equal_adjacent`: equal values on consecutive events
- `cycle_order_policy=nondecreasing_v1`: declaration of required
  continuous order for session verification

The counters appear in the finalized session manifest, not as claims
of actual PPU scanline timing. The recorder **still retains events**
after a decrease so they can be diagnosed. However, it refuses to
publish `complete=yes` when any cycle regression was observed.

When no CPU-cycle clock is available, all cycle counters must be zero;
the session can still verify for frame-only purposes, but the verifier
reports `cpu_cycle_order_verified=false`.

## Independent strict verification

`tools/verify_ppu_capture_session.py` reads the complete cycle log
and refuses a decrease at any row, **even if the whole-log and
per-frame Adler checksums have been recomputed**. The manifest must
declare zero total, same-frame and cross-frame regressions.

Equal adjacent clock values remain allowed. Their number must match
the independently counted `cycle_equal_adjacent` manifest field.
Counters above `2^53 - 1` are rejected because they cannot be
represented exactly by Lua's standard floating numeric type.

This is strict **monotonic nondecreasing observation**, not proof that
counter resets never occurred when no sampled event spans the reset,
or proof of the correspondence between CPU cycles and PPU raster dots.

## Diagnostic reports

`tools/analyze_ppu_cycle_trace.py` retains its existing
`cpu_clock_resets_or_discontinuities` counter for compatibility,
but adds same-frame and cross-frame decrease counts, equal-adjacent
counts and per-frame diagnostics. It sets
`counter_reset_proven=false`. A valid verified CLI session also
reports that the strictly nondecreasing counter check was passed.

The existing CPU-clock epoch split in diagnostics is a bookkeeping
convention only, **not** confirmation of an actual emulator reset.

## Regressions and evidence

- **54/54 Python tests passed locally**, comprising the 47 stage79–85
  session integrity tests and seven stage84 large-TSV streaming tests.
- **6/6 Lua callback scenarios passed locally** in LuaTeX, using the
  exact production `record_event` code fragment: increasing values,
  equal values, same-frame decrease, cross-frame decrease, multiple
  decreases, and no-cycle mode.
- Local and GitHub blob SHA-1 IDs match:
  - `tools/verify_ppu_capture_session.py`: `22ef72258b473cd50cbb19be30cc52b9430d6a8c`
  - `tests/test_ppu_capture_session.py`: `7623f6124f55896b257262952b148c452e3840aa`
  - `tests/test_fceux_ppu_counter_order.lua`: `a862755629630ebbc5896c0d0c09efe638665e43`
- Additional whole-collector Lua capture-session fixtures exercise
  decreasing values within a frame and across frames, as well as
  equal cycles. The Python diagnostic test file contains corresponding
  separate checks. Both are committed and picked up by CI, but **not
  independently confirmed by a completed GitHub runner execution**.

No original ROM, first-stage map geometry, authenticated gameplay
traces, raster verification or Nintendo Switch NRO was generated.
