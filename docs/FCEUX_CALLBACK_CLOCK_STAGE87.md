# Stage 87 — explicitly sampled FCEUX registerafter CPU clock

## Why this is not a PPU frame-boundary timestamp

The FCEUX `emu.registerafter` callback is invoked by the emulator on
an emulated frame boundary, but its `debugger.getcyclescount()`
reading is **a debugger CPU-clock observation at the time the callback
runs**. It cannot establish the original NES hardware's physical
VBlank, scanline, PPU dot, or exact frame-start CPU timestamp.

Stage86 correctly distinguishes the last logged event of one frame
from the first logged event of the next. Stage87 adds a separate,
explicitly named optional callback-time observation at captured
frames, rather than trying to infer one from register writes.

## Enabling the optional probe

In the owner's local FCEUX Lua console, **before** starting the
capture script, set:

```lua
VPD_CAPTURE_AFTER_CALLBACK_CLOCK = true
```

Then start `tools/capture_fceux_ppu.lua` as usual. The default is
**disabled**; this avoids introducing additional calls to the debugger
clock into existing trace-capture routines. If enabled, a missing
`debugger.getcyclescount` API causes an early refusal.

The producer samples the debugger clock **inside**
`emu.registerafter` for each **selected snapshot** (subject to
capture interval and limit), after flushing accumulated event records
but before reading the snapshot. The sample is saved in the
`frame_NNNNNN.meta.txt` file as:

```text
frame_callback_clock_scope=captured_frame_sample
frame_callback_cpu_cycle=<observed nonnegative integer>
```

Without the option, these fields read `disabled` and
`not_captured`. The finalized session manifest also contains:

```text
frame_callback_clock_mode=sampled_snapshots_v1
frame_callback_clock_samples=<number of successful samples>
frame_callback_clock_boundary_proven=no
```

A callback clock must be an exactly representable nonnegative integer,
not earlier than the most recent recorded event, and nondecreasing
across sampled snapshots. Impossible samples fail closed, incrementing
`callback_errors` and `capture_failures` rather than certifying the
session.

## Independent verification

`tools/verify_ppu_capture_session.py` enforces the manifest's mode,
sample count and `boundary_proven=no` safety declaration. When
enabled, it independently checks that each sample is between its last
committed CPU-cycle event and the next CPU-cycle event, if either
exists, and is nondecreasing across sampled snapshots.

This is a causal ordering **bracket** within the available callback
events. Its timestamps are not guaranteed to precisely coincide with
the PPU's internal rendering or VBlank transition.

## Regression suite

`tests/test_ppu_capture_session.py` includes ten stage87 cases for
valid bracketed callback samples, missing data, impossible samples,
incorrect mode/count, disabled mode, clock prerequisites, ordering and
overclaiming a proven physical frame boundary.

`tests/test_fceux_ppu_after_callback_clock.lua` uses invented
FCEUX events to exercise opt-in off, opt-in on and a deliberately
impossible second callback sample. It is linked to the existing
GitHub Actions workflow; **full execution is not yet verified**.

No original game ROM or visual resources are distributed. Any
successful isolated test only proves the specified instrumented
behavior, not full original gameplay timing.
