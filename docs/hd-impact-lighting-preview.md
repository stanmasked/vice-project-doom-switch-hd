# ROM-free manual combat — restrained hit lighting preview

This change introduces **optional, deterministic RGBA8888 impact light**
driven entirely by real `Simulation` hit-flash state.

It is a deliberately modest graphics-quality step, **not** an asset
restoration, not original NES lighting behavior, and not a claim of
original `Vice: Project Doom` artwork fidelity.

## Source of the light

The existing, source-controlled combat overlay supplies three
counters: `player_hit_flash_ticks`,
`guard.hit_flash_ticks` and `sentry.hit_flash_ticks`. The manual
Switch NRO opts into an authored localized amber/coral/cyan highlight
while one of those counters is positive and the corresponding live
enemy is visible. No collision, health, shooting, AI, enemy state or
camera position is modified by the renderer.

No external sprites, backgrounds or image assets are used.

## Safety and visual regression

- Output remains RGBA8888 with opacity `0xff` and fixed-point integer
  blending, deterministic across compilers and repeated draws.
- Glow radii are limited to 58–68 screen pixels. Invalid dimensions,
  null destinations, unbounded intensity and radius fail closed.
- Offscreen positions use 64-bit rectangle intermediates and clip
  safely; stride padding remains byte-for-byte untouched.
- Source-neutral `SceneView::hd_hit_lighting=false` preserves the
  existing golden screenshot, attract-mode frame hashes and synthetic
  source-art style exactly.
- `manual_controls=false`, or all impact counters zero, means no
  new lighting regardless of the feature flag.
- Portable renderer integration and a separate standalone C++ test
  verify source-hit visibility, determinism, no-hit identity, clipping,
  overflow safety and screenshot export not contaminated by opt-in tests.

The parent PR #39, already independently confirmed in NeXium,
contains the unmodified previous combat milestones. This parallel
graphics PR leaves that branch untouched. On-device rendering and
actual frame-rate performance of this lighting mode are **not yet
confirmed**; the Switch NRO must pass its own CI and NeXium run.
