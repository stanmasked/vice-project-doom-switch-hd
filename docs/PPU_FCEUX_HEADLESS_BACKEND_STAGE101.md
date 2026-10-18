# Stage101: FCEUX native PPU execution under two independent headless backends

Stage100 confirmed that a pinned, native, instrumented FCEUX binary
executed at least 8192 advancing newppu runppu steps on an original
synthetic NROM. The optional or legacy control processes exited early under
the Qt offscreen and SDL dummy drivers, so their renderer stability was
not proven. Stage101 isolates the display backend as a possible factor.

## Distinct graphical backends, same patched native binary

- Original: QT_QPA_PLATFORM=offscreen, SDL_VIDEODRIVER=dummy.
- Independent: Xvfb virtual X11 screen, QT_QPA_PLATFORM=xcb,
  SDL_VIDEODRIVER=x11.
- Both use dummy audio and software OpenGL for repeatable CI startup.
- The GitHub Actions build installs xvfb and xauth and runs the two
  headless modes sequentially without rebuilding the executable.
- Each mode must produce the strict positive newppu aggregate marker
  (8192 advancing calls, nonzero wraparound/label changes and zero
  invalid modulo updates). A failed positive control fails CI.

## Negative controls and diagnostic categories

Both backends also try newppu with the optional synthetic observer off,
and legacy PPU with the synthetic observer opt-in. Neither control may
emit a newppu marker. Remaining alive through the bounded observation
window is reported as clean, but this only asserts process liveness,
not independently observed rendered frames. Earlier exits are reported
as unverified_early_exit rather than passed.

Only fixed diagnostic categories are exposed in the printed marker:
signal_sigsegv, signal_sigabrt, qt_platform_initialization,
sdl_initialization, other_early_process_exit, and
not_an_early_failure. No native stdout, private paths, ROM bytes,
pixel data or raw PPU scanline coordinates are printed in public
summaries. Detailed emulator output is kept in ephemeral runner temp.

## ROM and evidence boundary

The test program is authored from scratch (tiny NROM PRG and zero CHR),
generated locally and never committed. No original Vice: Project Doom
assets, encrypted data, captures or gameplay raster events are used.
An Xvfb result is a software emulator headless-display comparison,
not an independent measurement of physical NES PPU/VBlank phase.
HD replacement stays disabled. Native original game geometry is
still unverified.

Test with:

    python3 -m unittest discover -s tests \
      -p 'test_fceux_stage101_headless_diagnostics.py' -v

Investigate any observed categories before declaring the legacy renderer
or disabled-observer startup stable. Do not infer PPU hardware timing
from raw internal FCEUX scanline counter changes.
