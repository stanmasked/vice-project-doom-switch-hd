# Manual combat HUD and hit feedback

This ROM-free presentation milestone stacks on PR #22, which confirmed
that a live NeXium X11 capture included 104 pixels of the original
synthetic guard's alerted torso after contact and zero after the
player's manual Y/Fire projectiles defeated the guard.

## Manual HUD layout

The former manual GUARD/HP indicators began at x=374 and overlaid
the title and second-line source disclaimer. The shared raster renderer
now reserves fixed, non-overlapping zones within the existing 76-pixel
header:

- Title at x=30..462 and disclaimer at x=32..548 (unchanged).
- Guard health begins at x=505; hero health at x=697. Both show filled
  and empty segments so zero HP can be distinguished from the UI
  disappearing.
- Dash status starts at x=611, with its separate cooldown bar at x=821.
  The optional alert / patrol / cleared state is shown to its right.
- External animation override metadata is moved beyond the combat HUD.

Only **manual gameplay** uses the new layout. The previous replay
demo's static bars, art and deterministic 200-frame loop are preserved.

## Damage feedback derives exclusively from gameplay

When a source-simulation projectile truly collides with the living guard,
`GuardEnemy.hit_flash_ticks` becomes 12. The existing torso is briefly
recolored and receives two small impact sparks. A genuine melee attack
sets `Simulation::player_hit_flash_ticks_` to 16, adds a brief highlight
over the hero's jacket, and temporarily warms filled health segments.
Both counters decay once per simulation step and reset alongside the
encounter; no renderer-only timers, external animation files or
hand-injected enemy hit events are used.

Counters contribute to encounter-enabled replay fingerprints only. In
the legacy demo encounter mode is off, preserving the original golden
no-combat replay hash.

## Verification

`tests/test_combat_hud_feedback.cpp` exercises real C++ simulation
projectiles and melee contact, checks the authentic flash values, and
renders actual RGBA8888 images through the same shared renderer used by
the Switch frontend. Pixel tests enforce that damage changes HUD chips
and effects **without modifying the title/disclaimer rectangles**.
The test also checks timed decay and that no guard UI is enabled in
the untouched demo.

The native Switch build and NeXium live input/screenshot audits must
also pass at this exact revision before claiming new on-screen effects
are verified. No original-game enemies, Nintendo proprietary art, ROM
or firmware are included; these are self-authored prototype visuals.
