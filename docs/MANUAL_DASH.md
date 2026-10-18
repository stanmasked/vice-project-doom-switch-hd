# ROM-free manual dash prototype (research stage)

This work adds a **new, self-authored mechanic** to the independent libnx
test-scene, not recovered Vice: Project Doom behavior. It builds on the
verified guest manual controls and native NeXium guest-exit proof in PR #16.

## Controls

- Direction + **ZR**: start a short grounded dash in that direction.
- Six simulation ticks of movement at 6 pixels per tick, compared with the
  normal 2 pixels per tick; facing is locked to the dash direction.
- 45 simulation ticks of cooldown (counting from dash initiation), with
  **release before the next activation**. Holding ZR cannot retrigger.
- Wall collision immediately cancels remaining movement, preserving
  the existing per-pixel swept collision.
- Airborne and directionless attempts have no dash effect. Jumping,
  horizontal controls and shooting otherwise retain their existing rules.
- In manual mode, hold **StickL + ZR** to reset terrain art instead.
  In autoplay, ZR retains the old terrain-reset behavior.

## Determinism and presentation

The portable simulation owns dash duration, direction, cooldown and
input-edge state, and includes them in its replay fingerprint only when
dash state has been used. Existing auto-demo input does not contain Dash,
so its pinned 200-frame replay hash and associated graphical scene are
left untouched.

Both libnx and native-host raster tests use `applyCombatOverlay()`
to present dash state: a short horizontal motion trail and a cooldown
indicator visible in **manual mode only**. The manual HUD indicates the
new ZR binding. A native C++ dash gameplay test requires identical replay
fingerprints across repeat scripts, bounded six-tick movement, cooldown
and edge handling, early cancellation at walls, rejection while airborne,
leftward dash and complete reset. A separate host renderer regression
checks actual pixel differences with dash trail and cooldown indicator
enabled versus disabled.

## Evidence boundaries

The Native Simulation, Graphics and Switch-NRO CI workflows are responsible
for confirming compilation and regressions after this change. NeXium's
existing seven-event manual witness deliberately keeps its strict schema;
it does **not** claim that ZR was exercised inside the emulator until an
independent guest-native dash witness is implemented. Frame pacing,
performance on physical Switch, original NES gameplay equivalence and
the NeXium GUI lifetime remain outside this stage's claims.
