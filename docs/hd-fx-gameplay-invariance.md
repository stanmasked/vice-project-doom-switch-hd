# Manual HD FX gameplay invariance — ROM-free core

## Goal

The prior NeXium proof establishes *actual* pad L+R edges and pixel changes
on the live fourth-stage guest frame. This extension checks a separate
failure mode: changing HD visuals must not change game rules, health, AI,
projectiles, collision, stage progress or replay determinism.

`tests/test_hd_fx_simulation_invariance.cpp` drives **two distinct
`Simulation` objects** with identical input on 350 manual ticks. One
always renders with the four existing HD layers enabled; the other toggles
those layers OFF/ON during manual gameplay. After *every tick*, the two
`Simulation::fingerprint()` values must agree.

At eight source-derived checkpoints, both scenes are independently rendered
via the same `applyCombatOverlay` adapter as the native Switch frontend.
A fixed scene ROI excludes the HD-mode HUD text. The four OFF comparisons
must differ in scene pixels and the four ON comparisons must match. Calls to
`drawScene` must not mutate either simulation fingerprint.

Separately, the regression verifies that:
- autoplay ignores L+R and produces identical scene pixels;
- leaving manual mode retains the selected visual preference;
- source-derived guard contact can lead to a real simulation defeat;
- explicit Minus retry restores hero/enemy state while the frontend's HD
  preference remains OFF;
- the first resumed Right movement remains identical in both simulations.

This is **independently authored ROM-free gameplay**. No original NES physics
or sprite artwork are reconstructed or certified. These native host tests
are not substitutes for the already verified NeXium guest L+R evidence or
physical Switch hardware testing.
