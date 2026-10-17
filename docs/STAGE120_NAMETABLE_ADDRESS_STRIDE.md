# Stage120 — buffered nametable address stride across rendered pixels

## What Stage119 did not rule out

Stage119 linked a real newppu nametable tile-ID read to its buffered
`BGData` record and an observed `XBuf` pixel. It checked the fetched
address was in `$2000–$2FFF` and that its low bit matched the alternating
synthetic tile ID. This leaves an ambiguity: `$2002` and `$2402`
have the same parity and can carry the same tile ID and CHR planes.

Stage120 is a **second, stricter synthetic-ROM witness**, not evidence
that Vice: Project Doom itself has been captured or reconstructed.

## Additional native evidence

The exact `NTRefreshAddr` captured by the Stage119 fetch hook stays in
the tile's `BGData` record. When newppu consumes that record for each
pixel, the Stage120 check asserts the actual address equals:

```text
expected = observed_row_base + ((pixel_x + current_fine_x) >> 3) + coarse_phase
```

This equation is intentionally scoped to the Stage119 synthetic fixture:
the nametable writer initializes all four name tables, the sampling
window is the first 16 pixels of two known scanlines, and the test
expects the first phase's *column offsets* `0/1/2` and the second
phase's offsets `1/2/3`. Row bases are observed from the buffered first
source address and cannot be assumed to equal `$2000`.

Per 16-pixel window, the observer checks **16 addresses and two
contiguous tile-address transitions**. Across four independent fine-X
phases (`1,3,5,7`) that makes 128 pixel-address checks and 16 expected
tile transitions. No raw pixels, ROM bytes, or original-game art are
logged.

A standalone Stage120 marker must appear in each native FCEUX log
**before** the Stage119 PASS marker. The Python auditor matches the two
certificates, rejects duplicates, contradictory values or a rejection
marker, and then verifies the complete four-run sweep. Uniform-CHR and
observer-disabled runs still serve as separate negative controls.

An independent C++11 regression deliberately changes one buffered
nametable address to its `+$0400` page alias. Stage119's parity and
observed-color checks still pass; Stage120 must reject it.

## Verification

```bash
python -m unittest discover -s tests -p 'test_fceux_stage120_nt_stride.py' -v
```

The existing pinned FCEUX native job runs
`tools/run_stage119_native_nametable.py`, which now also requires the
Stage120 marker and verifies the complete four-phase sweep. A passing
Python fixture is **not** proof of a passing real FCEUX build: the
pinned CI result must be checked independently.

## Boundaries

Only Stage119's generated, deliberately differentiated Mapper-4 ROMs
are eligible for these address expectations. Do not reuse the base
`$2000` assumption for actual game frames, arbitrary camera positions
or mapper mirroring. The observer is emulator-specific; it does not
establish NES hardware dot accuracy, level geometry, original scroll
events, true graphics assets or Switch rendering fidelity.
