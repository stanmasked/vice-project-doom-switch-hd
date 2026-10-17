# Stage97 — pinned FCEUX PPU hook-site analysis and C++ candidate bridge

This stage inspects **real upstream FCEUX source** at revision
8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8
in TASEmulators/fceux/src/ppu.cpp. The matching original Git blob ID is
ce84a9df2c12b737fb13316737add1e9963a3ff7.
Reference:
https://github.com/TASEmulators/fceux/blob/8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8/src/ppu.cpp

The upstream code has two distinct implementations:

- Legacy loop FCEUPPU_Loop, which may dispatch to FCEUX_PPU_Loop if
  newppu is selected. It is **not safe** to infer dot-level fidelity
  from the legacy path.
- New PPU loop FCEUX_PPU_Loop. Native getters newppu_get_scanline and
  newppu_get_dot return ppur.status.sl and ppur.status.cycle, but
  the visible renderer sets yp=sl-1. The new PPU loop sets
  PPU_status |= 0x80 directly and comments that timing may be off.

**Consequently raw sl/cycle values, renderer scanline labels and hardware
NES scanlines are NOT automatically interchangeable.** The stage96
NTSC golden contract cannot simply be grafted onto these counters.
Real integration must verify phase, VBlank transition placement, odd
frame dot skip and legacy fallback first.

## Work shipped

- tools/audit_fceux_native_ppu_hook_sites.py: opt-in source anchor checker,
  pinned revision metadata and exact original Git blob check. This
  audit does not patch the emulator or claim a compiled native hook.
- tools/fceux_native_ppu_raster_adapter.h/.cpp: stand-alone C++17 candidate
  event writer; accepts pre-normalized *synthetic* frame, scanline, dot
  and event-kind entries. Rejects regressions, invalid VBlank markers,
  bad coordinates and incomplete frame traces before finish.
- tests/native_ppu_raster_adapter_smoke.cpp: synthetic event driver.
- tests/test_fceux_native_ppu_adapter.py: compiles the actual C++ bridge
  under a system C++ compiler, verifies its output with the independent
  Stage96 Python validator, and tests fail-closed cases. No FCEUX
  or commercial ROM is required in CI.

The C++ bridge intentionally does **not** claim native PPU hook
installation, derive NES coordinates from ppur.status or output original
game register values. Even a valid bridge-generated trace is only
synthetic evidence with original game identity and HD geometry unproven.

## Pinned source audit from a local FCEUX checkout

Use a source tree at the exact revision above and run:

    python3 tools/audit_fceux_native_ppu_hook_sites.py \
      /path/to/fceux/src/ppu.cpp --require-exact-blob

The full blob check only accepts unmodified pinned upstream ppu.cpp.
A future patched native tree will need a separate pinned commit
and independent patch review.

## Next stage / requirements

1. Design native PPU *tick-level* instrumentation point with a verified
   before/after tick contract, not simply the Lua frame callback.
2. Account for frame-start definition versus newppu renderer offset and
   oldppu/newppu runtime selection.
3. Independently run synthetic benchmark traces against real patched
   FCEUX source. Only then label any observed scanline/dot as native
   raster data. Camera path, original game assets and first-level HD
   substitution remain blocked.

Native source license remains with FCEUX: no source copy or proprietary
game material has been vendored or published.
