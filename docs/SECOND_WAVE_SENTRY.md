# ROM-free stage expansion: ranged sentry and exit gate

This phase stacks on PR #23, whose manually controlled guard encounter,
damage HUD and real NeXium X11 battle snapshots all passed. The existing
guard at x=16 tiles remains unmodified; original seven manual input events,
six-tick ZR dash, live first-guard kill and frozen auto-demo witness are
the regression baseline.

## Sequential prototype stage

The new content is gated in the normal manual gameplay simulator:

1. Defeat the first three-HP guard with authentic swept projectiles.
2. Advance to x>=26 tiles. Only if the original guard has zero HP and
   the player survives does a **second wave** become active.
3. Approach a stationary two-HP **ranged sentry** at x=39 tiles.
   When the player is within 160 pixels at compatible vertical height,
   the sentry emits one hostile projectile every 42 simulation ticks.
   Hostile shots travel horizontally at three pixels per tick, with
   one-pixel terrain/player collision sweeps, a 90-tick lifetime and
   an explicit three-slot bounded pool. They deal one damage and trigger
   the same actual source-driven player flash.
4. Two real player projectile hits defeat the sentry; on reaching the
   corridor exit at x>=55 tiles with health remaining, the stage is
   flagged **clear**.

The turret and hostile projectiles remain absent in all earlier
single-guard tests, in the original demo and before the stage gate.
The repeatable game-state fingerprint serializes second-wave shots,
cooldowns, health and stage-clear state only **after second wave
activation**, so previous native witness/attract-mode hashes stay
unchanged.

## Visible integration

The existing shared render adapter now exposes an optional sentry,
three hostile projectile slots and the stage-completion flag. The NRO
renders a distinct teal mechanical turret, its two HP chips, a red
hostile shot, and HUD text for the wave, open exit and stage-clear
state. No new art or ROM assets are needed.

Portable C++ tests verify gated progression, hostile hits, repeatable
combat, turret defeat, exit requirements, reset and demo preservation.
RGBA tests verify source-driven sprite, HP and hostile projectile pixels.

**Scope:** this is a new self-authored level prototype, not recovered
stage geometry, enemies, timing, or game mechanics from the original
Vice: Project Doom. Native Switch compilation does not prove second-wave
play inside NeXium until a separate actual guest witness is produced.
Physical Switch hardware remains untested.
