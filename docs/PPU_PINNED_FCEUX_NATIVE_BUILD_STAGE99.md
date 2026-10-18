# Stage99 — full pinned native FCEUX build with raw newppu hook

Previous stages compiled only the stand-alone C++ candidate and a mock
source-injection test. Stage99 adds **an independent GitHub Actions job**
that fetches an actual pinned FCEUX source checkout and attempts a
**complete Qt/SDL Linux FCEUX executable build** with Stage98's diagnostic
hook enabled.

## What the separate CI job checks

- A fresh, depth-one Git checkout is made at exactly
  `8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8`.
- `src/ppu.cpp` must match its independently pinned original Git blob,
  `ce84a9df2c12b737fb13316737add1e9963a3ff7`.
- The checked Stage98 source patcher produces a separate output tree in
  the temporary runner filesystem; the untouched repository checkout is
  never modified.
- The resulting `src/ppu.cpp` differs in an explicitly guarded
  `runppu(int x)` raw internal scanline/cycle callback only.
- CMake compiles and links the real `fceux` executable with
  `-DVPD_NATIVE_RAW_PPU_PROBE`; the pipeline confirms it exists and
  is executable.
- No game ROM is fetched, no game screen is captured, and no FCEUX
  executable or upstream source file is uploaded as an artifact.

The workflow installs Qt5, SDL2, OpenGL, minizip, zlib and libarchive
development dependencies in the **ephemeral** GitHub runner. The
integration build lives in a separate job named
`pinned-fceux-native` so C++/Python and Lua regressions remain
independently visible.

## Limits

Successfully linking a patched FCEUX proves compatibility with the pinned
upstream source and build dependencies, **not** correctness of runtime
scanlines or physical VBlank. There is intentionally no native sink
registered, and the compiled binary must not be described as a verified
first-level PPU capture. The runtime hook still records raw internal
`sl`, `cycle_before`, `cycle_after`, `end_cycle` and advance
amount without NES raster normalization.

No original game's sprites/background, scroll trajectory or HD level
geometry is reconstructed. HD replacement remains disabled.

## Next gate

Develop a no-ROM runtime observation harness and independently validate
how FCEUX newppu raw tick counters relate to frame starts, missing dots,
VBlank and legacy PPU fallback. Enable raster claims only after those
measurements agree with separately checked NTSC timing references.
