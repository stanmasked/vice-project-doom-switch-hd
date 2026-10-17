# Stage 80 — atomic FCEUX video event capture on counter failures

## Defect and risk

Before stage80, `tools/capture_fceux_ppu.lua` appended the row to
`mmc3_video_writes.tsv`'s in-memory buffer **before** calling
`debugger.getcyclescount()`. If that call raised an exception or
returned an unsupported value, the corresponding
`mmc3_ppu_cycles.tsv` row was not appended.

The callback also did not increment `callback_errors`, because the
counter validation used a bare `assert`. If execution continued to
`emu.registerexit`, `complete=yes` might be emitted despite
different event streams. A subsequent verification could detect the
divergence, but production should never certify it.

## Correction

The stage80 callback performs these operations in order:

1. `pcall(emu.framecount)` and validate an integral frame in
   `[0, 2147483647]`.
2. Construct the frame TSV row locally, without appending it.
3. If CPU cycle capture is enabled, `pcall(debugger.getcyclescount)`,
   validate an integral cycle count in `[0, 9007199254740991]`,
   and construct the cycle TSV row locally.
4. Only after both rows exist, append them to their respective buffers
   and increment the shared event count.

All invalid/throwing frame and cycle calls invoke the existing
`checked` routine: it increments `callback_errors` before raising.
No half-records are appended. `flush()` now fails closed if its
buffer lengths differ when cycle capture is enabled.

Per-frame metadata remains **prefix-only**, and the finalized stage79
session manifest requires `callback_errors=0` for `complete=yes`.
A collector that cannot safely timestamp all requested events
therefore cannot certify the session.

## Synthetic tests

`tests/test_fceux_ppu_cycle_atomic.lua` mocks FCEUX and runs both
a CPU-cycle-enabled and a no-cycle scenario. It injects these failures
between two valid callbacks:

- Cycle counter throws, returns `nil`, a negative number, a fraction,
  NaN, positive infinity or an unsafe integer.
- Frame counter throws, returns `nil` or an out-of-range integer.

The test expects **exactly two logged events**, matching R/W kind in
CPU-cycle mode, the exact accumulated `callback_errors` count,
`register_log_complete=no`, and `complete=no` in the final
session manifest. The failure rows must be absent. Both runs clean up
their synthetic outputs.

The new Lua integration test is linked to the native GitHub Actions
job. It has **not yet been run successfully against the complete
up-to-date private repository** in this environment.

A standalone local LuaTeX (Lua 5.3) regression using the **same
production `record_event` implementation** completed successfully:
**10 malformed callback attempts rejected, 2 valid frame/cycle
records retained, 0 one-sided rows**. This verifies the key callback
logic, but not the full FCEUX collector's file I/O or live behavior.

## Known limits

Matching event rows and source-checked counters improve consistency,
not ROM identity, scanline fidelity or video hardware timing. The
existing session validator independently checks event equality when
a CPU-cycle stream is present. Real gameplay capture, verified
first-level geometry and Switch NRO are still outstanding.
