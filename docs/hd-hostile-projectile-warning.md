# HD hostile projectile warning halo — ROM-free scene

A small, opt-in authored visual cue for the existing synthetic wave-two
sentry projectiles. This is **not** extracted NES art or verified original
Vice: Project Doom gameplay.

## Source and layering

`SceneView::hd_hostile_projectile_halo` defaults to false and the
Switch graphical prototype enables it only in real manual-control mode.
The effect requires an enabled wave-two sentry, an uncleared stage, and
one or more **active** source-owned enemy projectile slots. These are
already populated by the tested simulation → render adapter.

Each projectile contributes a deterministic, 30-pixel-radius, low-energy
red/orange light to the existing scenery. No new random source, tick,
texture, projectile location, AI rule, hitbox, timer or physics update is
introduced. The regular hostile projectiles remain at their existing
positions and colors.

The tint is composited after terrain but **before** guard, sentry and
hero sprites, preserving the exact alert-red and damage-flash sprite
colors already used by independent NeXium X11 identity checks. It is
fully inactive for scripted demo playback and defaults off for host
users who construct `SceneView` without opting in.

## Regression gate

`tests/test_scene_renderer.cpp` requires:

- a real active hostile projectile visibly affects the RGBA scene;
- the identical scene/flags produce identical frame checksums;
- an alert guard torso keeps exact original packed RGBA
  `0xff5d67dc` with the hostile halo present;
- the effect has no pixel difference without active projectiles,
  without an enabled wave-two sentry, on a cleared stage, or in
  the legacy replay demo;
- framebuffer stride padding stays unchanged.

The approved synthetic golden auto-demo frame and previously verified
same-frame hero hit light/footstep proof are not redefined. Acceptance
requires native/graphical host tests, Nintendo Switch NRO cross-build,
NeXium, strict guard colors, fourth gameplay stage-clear and existing
same-frame dust and hit-light evidence to pass again.

NeXium results do not prove physical Switch frame rate or proprietary
NES-game graphics fidelity.
