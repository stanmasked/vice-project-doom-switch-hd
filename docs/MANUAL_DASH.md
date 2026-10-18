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

## NeXium guest ZR input capture

The input mapping is grounded in the NeXium source
(`nexium-gui/src/controller_config.rs`): default keyboard `T` is **ZR**,
and `D` is the left-stick right direction. The X11 test now sends D+T
after the existing right/fire/jump/left manual verification, and before Plus.

A new guest-only `dash_witness.txt` is truncated during NRO startup and
receives no events from the host. The actual libnx gameplay loop records:

1. `start` only when the live simulation consumes ZR+Right, moves by
   1,536 fixed-point units (six pixels), enters the dash state and starts
   its 45-tick cooldown.
2. `complete` only five further gameplay ticks later, after a total
   9,216 fixed-point units (36 pixels), with the dash completed and
   40 cooldown ticks remaining.

A new independent `tools/audit_nexium_dash_guest.py` requires exactly
these two guest-generated records, strictly ordered field schemas and
frame intervals. The native runner also requires the existing seven-event
manual witness, normal kernel-level NRO exit proof and matching host
injection record. The mutation regression tests reject host-only,
missing, altered and reordered evidence.

This new CI assertion is **not** considered proven until the
`NeXium Vice runtime smoke test` for the exact commit passes.
The feature remains a synthetic homebrew mechanic, not original game
parity or physical Nintendo Switch performance evidence.
