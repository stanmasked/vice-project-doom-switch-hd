# Stage 75 — fail-closed MMC3 callback errors and capture completeness

## Defect

The stage74 mirrored bank-register hooks covered CPU $8000–$9FFF, but
stages38/45/49 did **not consistently record invalid write callback
arguments as capture errors**. If a malformed callback raised and the
emulator later invoked the exit hook, those traces could be labelled
`complete=yes`, despite an unobserved or rejected mapper write.
That would make the inferred physical PRG bank unreliable.

## Changes

- **Stage38 dispatch + RAM:** all mirrored MMC3 and tracked RAM writes
  check actual address, `size == 1`, and integer 8-bit write value.
  Contract violations increment `callback_errors` before raising.
  Metadata now includes this count. `trace_complete=yes` requires
  both zero dropped events and zero callback errors.
- **Stage45 PRG reads:** mirrored MMC3 write arguments now use the
  same checked failure path as READ callback verification; a bad
  address, size or value is counted rather than silently leaving a
  nominally complete log.
- **Stage49 joint stream:** same complete error-counting behavior for
  mapper writes and READ callbacks.
- **Stage53:** already used an explicit `checked` routine, so its
  existing capture and metadata logic remains unchanged.
- **Stage38 Python analyzer:** `callback_errors` is mandatory metadata,
  and the completeness flag is cross-validated. In normal mode an
  incomplete log is rejected; `--allow-incomplete` remains for
  *diagnostics only* and now reports the callback error count.

If the emulator halts on an exception **before running an exit hook**,
the metadata file may be missing entirely. Validators already refuse
such a capture. A partial TSV must never be used alone as valid
first-level evidence.

## New negative tests

Stage38 synthetic execution tests now include a `VPD_MOCK_BAD_MMC3=1`
mode. It triggers four malformed callbacks (MMC3 address, size, byte,
and RAM hook address), while ensuring metadata records
`callback_errors=4`, `trace_complete=no`. The CLI analyzer tests
check that the log is rejected in normal mode and can be examined in
diagnostic mode without upgrading its evidence level.

Stage45 and stage49 Lua tests similarly inject three malformed MMC3
writes after an invalid READ zero sentinel and require
`callback_errors=4` and `complete=no`.
The CI workflow includes the new stage38 mode:

```sh
VPD_MOCK_BAD_MMC3=1 lua5.4 tests/test_fceux_dispatch.lua
```

Other existing FCEUX Lua tests remain in the native CI job.
The stage38 mock's mirrored-write TSV assertions were also corrected
to use real tab escapes.

## Verification boundary

The patches, tests and workflow changes are committed to draft PR #3.
Their correctness is supported by source review and the synthetic
test design, **not** a fresh full local run of the changed stage38,
stage45 and stage49 tests. The available local snapshot contains
an earlier stage74 subset focused on stage53; those five older tests
passed, but do not validate these latest changes.

GitHub Actions must allocate a runner before full Python/Lua/C++
regression results can be claimed. No original ROM bytes, verified
first-level geometry, or Switch NRO are produced by this stage.
