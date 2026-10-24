# Vice: Project Doom HD Remake — Stage366 lifecycle regressions

**Result: PASS at native test level.** This stage strengthens the source-safe manual scroll DEMO lifecycle without changing the NRO runtime source. The actual NeXium 41-state framebuffer trace remains the Stage365 result; Stage366 does not claim a second real-emulator pause/restart replay.

## CI evidence

- [Native Core CI #40075342571](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/40075342571) — **Success**. All **73/73 CTest cases** passed; Python CI reported **1,426 tests** passing.
- [Nintendo Switch graphical scene #40075342564](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/40075342564) — **Success**. Exact-source Switch NRO build and all **73/73 host raster tests** passed.
- [Deterministic native simulation #40075342548](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/40075342548) — **Success**, both Release and Debug, **29/29** each.
- Tested commit: `940475d2c094fae4aed77992ed61999743b63327`.

## What changed

Extended `tests/test_driving_source_scroll_demo.cpp` with a manual-exit lifecycle scenario:

1. Start from a fresh explicit controller edge; the first presented reference pair must be 519.
2. Leave manual driving; the demo must turn off, clear the overlay and reset its next pair to 519.
3. Attempt to resume without a fresh controller edge; it must remain off.
4. Supply a fresh edge; the sequence must restart at 519 and advance to 520 on the next contiguous guest tick.
5. Send a fresh chord while active; it must cancel the demo, and the next frame must not leak the overlay.

The existing dropped-guest-tick and repeated-guest-frame checks remain in place and passed. The shared raster witness is validated on every one of the 41 synthetic host-rendered demo states, with pixel perturbations rejected.

## Evidence boundary

This is native state-machine and host raster testing. It does not claim that a pause/restart was separately executed inside NeXium. The Stage365 real NeXium run remains the independent evidence that all 41 source-safe states are presented by the ROM-free NRO in the emulator. It does not authenticate original NES source frames or prove original camera/vehicle physics.

PR #99 remains Draft. No merge or main-branch change was performed.