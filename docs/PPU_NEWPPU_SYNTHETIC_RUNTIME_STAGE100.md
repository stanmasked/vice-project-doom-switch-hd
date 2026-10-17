# Stage100 — execution of instrumented FCEUX with an original synthetic NROM

Stage99 linked actual upstream FCEUX. Stage100 additionally runs that
executable in a headless Qt/SDL environment with an independently authored
minimal NES/NROM test program. No commercial ROM, graphics, audio, screenshots,
game maps or original captures are used, committed, or uploaded.

## Runtime witness

The Stage98 native `runppu(int x)` probe requires two compile-time definitions
(`VPD_NATIVE_RAW_PPU_PROBE` and `VPD_NATIVE_SYNTHETIC_SMOKE`) plus the runtime
opt-in `VPD_STAGE100_SYNTHETIC_SMOKE=1`. Without these gates, the synthetic
observer does not install itself or produce any diagnostic marker.

The runtime witness counts 8192 **advancing** native newppu calls, validates
raw modulo-cycle transitions, and counts internal cycle wraps and changes to
FCEUX's internal scanline label. The real native source may also call
`runppu(0)`; Stage100 counts these separately as zero-advance calls, not as
physical PPU dots and not as malformed counter events.

The observer emits one bounded aggregate marker and detaches. It never
exports raw line/dot positions, CPU/ROM bytes, palette, CHR, screen pixels,
or private game identities.

## Synthetic ROM

`tools/make_stage100_synthetic_nrom.py` creates an iNES header, one original
16 KiB NROM PRG bank, an intentionally blank 8 KiB CHR bank, and reset vectors.
The tiny 6502 program enables the background and then loops. The generated
`.nes` file lives only inside the GitHub runner's temporary directory.

## Positive and negative controls

`tools/run_stage100_fceux_synthetic_smoke.py` invokes the actual freshly
built FCEUX binary with `QT_QPA_PLATFORM=offscreen` and dummy SDL video/audio.

- Positive: `--newppu 1` with all probe opt-ins must emit a strict single
  8192-step native runtime marker with zero malformed raw step observations.
- Independent negative: the same `--newppu 1` emulator and synthetic ROM
  with `VPD_STAGE100_SYNTHETIC_SMOKE=0` must *not* produce a marker and
  must stay alive until the harness terminates it.
- Exploratory legacy check: `--newppu 0` must not emit the newppu marker.
  An early process exit is reported explicitly as
  `legacy_renderer_status=unverified_early_exit`, **not** a successful
  old-PPU execution test. The virtual-display crash needs further diagnosis.

All subprocess runs are bounded. No synthetic-ROM files or native executable
are uploaded as GitHub artifacts. Regression tests also cover missing,
duplicated, malformed and implausible runtime markers.

## Remaining evidence gates

Raw newppu counters are **not** authenticated NES hardware scanline/dot
positions. The runtime smoke does not establish actual VBlank transitions,
odd-frame dot behavior, mapper CHR visibility, correct rendering of the
original first level, or camera motion. The original game and HD graphics
replacement remain outside CI and the HD substitution gate remains closed.

Upcoming work: diagnose the oldppu virtual-display exit separately, then
independently calibrate native PPU counters and VBlank against verified
synthetic and physical PPU timing references.
