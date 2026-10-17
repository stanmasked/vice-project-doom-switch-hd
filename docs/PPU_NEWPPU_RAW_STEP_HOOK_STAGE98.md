# Stage98 — opt-in native newppu raw-step hook (private patch candidate)

This stage adds a **working source-injection prototype** to the **exact**
upstream FCEUX ppu.cpp identified in Stage97, without incorporating FCEUX
source into this repository and without distributing private capture data.

## Why this instrumentation point

At revision 8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8,
FCEUX src/ppu.cpp implements runppu(int x) as an internal modulo
update of ppur.status.cycle followed by X6502_Run(x). The PPU step
amount x is not invariably 1. ppur.status.sl is a **native internal
counter**; it is not yet a proven NES hardware raster scanline.
Legacy FCEUPPU_Loop follows a different path.

Consequently Stage98 records only:
- raw ppur.status.sl (internal label);
- cycle immediately before / after the increment;
- internal cycle modulus and advance amount.

No frame, scanline or dot is converted to Stage96 raster positions, and
no VBlank event is asserted. Do not connect this hook directly to the
Stage96 normalized event validator without independent native timing
correlation.

## New files

- tools/build_fceux_newppu_probe_patch.py: requires a specific upstream
  Git blob of FCEUX src/ppu.cpp, anchors the exact runppu modulo update,
  refuses ambiguous, previously patched, or changed source, and writes a
  separate **private output tree**. There is no supported CLI flag that
  disables the pinned-blob requirement.
- tools/vpd_newppu_raw_step_probe.h: dependency-free C++11 observer
  with optional callback and raw modulo arithmetic checks. No callback
  or file output is installed implicitly.
- tests/test_fceux_newppu_probe_patch.py: ROM-free C++ compilation of
  the *injected* synthetic runppu under both compile configurations,
  checking raw before/after values, CPU continuation, safety gates and
  deliberate patch rejection scenarios.

## Local workflow

Using a local FCEUX checkout at that exact revision:

```bash
python3 tools/build_fceux_newppu_probe_patch.py \
  /path/to/fceux/src/ppu.cpp private/fceux_stage98_candidate
```

This produces a **new** src/ppu.cpp and
src/vpd_newppu_raw_step_probe.h under private/fceux_stage98_candidate.
It does **not** modify your checkout.

The hook is compiled out unless VPD_NATIVE_RAW_PPU_PROBE is explicitly
defined. Even when compiled in, it has no file output and no callback
until a separate native consumer explicitly sets the sink. It is not a
complete or compiled FCEUX fork, and has not run against an actual ROM.

## Validation and next gate

The regression tests prove native C++11 compilation of an instrumented
**synthetic source stub**, not a full FCEUX binary build. A native FCEUX
build and independent PPU hardware phase checks remain necessary. In
particular: odd-frame skipped dot, legacy fallback, internal frame origin,
VBlank status changes and callback re-entry under CPU execution must be
validated before any label can be called a physical PPU scanline.

All real ROM identity, background ownership, camera reconstruction and HD
first-level geometry gates remain **closed**.

Pinned upstream source:
https://github.com/TASEmulators/fceux/blob/8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8/src/ppu.cpp
