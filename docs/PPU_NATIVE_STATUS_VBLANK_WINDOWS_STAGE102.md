# Stage102 — FCEUX source-level VBlank status-assignment windows

Stage101 demonstrated that the pinned newppu FCEUX binary runs under
Xvfb/X11 and that the dummy Qt/SDL backend suffers SIGSEGV during certain
control launches. Neither backend validates *physical NES VBlank*.

Stage102 adds two **pinned source-level probes** in FCEUX's
`FCEUX_PPU_Loop()` at revision
`8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8`: immediately after
`PPU_status |= 0x80` in the newppu loop and immediately after
`PPU_status = 0` prior to its scanline-render loop. They are assignments
made by the emulator, **not necessarily actual PPUSTATUS transitions**;
in particular CPU reads of $2002 may clear VBlank independently.

The exact original upstream Git blob, byte-for-byte Stage98 patch,
unique status-write contexts, and original line endings are verified
before generating a private candidate. Source patching, compilation
and local runtime execution happen only on the temporary GitHub runner.

## Raw timing measurement

The existing `runppu(int x)` hook now accumulates the requested
**internal tick units** (`x` when positive) separately from counts
of callback invocations. Calls with x=0 are recorded separately.
At each observed VBlank flag assignment, the Stage102 observer
records a private monotonic cumulative tick total. After three
enter/clear pairs, a single bounded marker reports:

- Source-level VBlank-start assignment count: 3
- Source-level VBlank-clear assignment count: 3
- Minimum/maximum tick interval between adjacent start assignments
- Minimum/maximum tick interval from start assignment to clear assignment
- Invalid assignment ordering or nonpositive intervals

No original PPU raster positions, ROM bytes, pixels, palette, CHR
registers, CPU registers, full event traces or screenshots are
written to public build logs. Only synthetic-ROM aggregate intervals
are printed. Negative/invalid checks fail closed.

## Build and run on synthetic NROM

The native workflow compiles real pinned FCEUX with all three opt-ins:
`VPD_NATIVE_RAW_PPU_PROBE`, `VPD_NATIVE_SYNTHETIC_SMOKE` and
`VPD_NATIVE_SYNTHETIC_VBLANK`. Stage102 additionally requires runtime
`VPD_STAGE102_STATUS_PROBE=1`; outside this gated context its reporter
does not run.

The real runtime smoke runs **only under Xvfb/X11**, since Stage101
isolated dummy Qt/SDL crashes. It boots a newly generated original
minimal NROM from temporary local files, not the Vice: Project Doom ROM.
The verifier requires exactly one well-formed three-pair marker with
monotonic nonzero tick intervals and no invalid assignment pairing.

Command to test only the ROM-free unit and C++-header behavior:

    python3 -m unittest discover -s tests \
      -p 'test_fceux_stage102_status_windows.py' -v

## Trust boundary

FCEUX's internal `ppur.status.sl` and `status.cycle` are not asserted
to map directly to NES physical scanlines or raster dots. Tick units
are requested emulation steps, not independently measured time.
Even exactly spaced source-level PPU_status assignments cannot establish
real VBlank edges, visible pixels, original game's map geometry,
CHR bank effects, camera motion, or HD-rendering readiness.
HD replacement remains disabled until the original first level is
separately evidenced and rendered correctly.

Upstream revision reference:
https://github.com/TASEmulators/fceux/blob/8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8/src/ppu.cpp
