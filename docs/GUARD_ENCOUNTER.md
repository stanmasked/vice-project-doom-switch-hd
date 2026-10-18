# ROM-free guard encounter — first enemy gameplay prototype

This change stacks on PR #17's confirmed native manual ZR dash and its
independent NeXium event witness. It does **not** use the NES ROM or original
game art and makes no claims about the original Vice: Project Doom AI.

## Behavior

When entering the **manual** Switch play mode, the simulation enables one
synthetic 3-health guard at tile x=16. The existing autonomous 200-frame
demonstration never enables him and keeps its pinned replay fingerprint.

- Patrol: one pixel per simulation tick within tiles x=14 through x=20.
- Detection: a hero within 144 horizontal pixels and within one player-height
  vertically triggers pursuit; the state is visible on the guard.
- Contact attack: at up to 20 horizontal pixels, the guard takes one point
  from the hero's initial five health, then respects a 32-tick attack cooldown.
  Health is bounded at zero. The guard's attack and death stop further damage.
- Projectile hits: the existing per-pixel swept shots check the guard before
  the stationary training target, after terrain collision. Three direct hits
  reduce the guard from 3 to 0 health and turn off his visuals and pursuit.
- Solid walls can block player bullets; guard movement is bounded by
  patrol limits and the game's collision map.
- The guard's position, direction, alert flag, cooldown, hits, attacks, and
  player health are included in the explicit replay-state fingerprint
  **only when the optional encounter is enabled**.

## Shared presentation and tests

`applyCombatOverlay()` carries the same guard from portable simulation into
both the libnx raster renderer and native host raster tests, without mock
sprites. A small procedural guard silhouette and health/alert accents are
drawn only if the encounter is enabled, together with a five-segment player
health HUD in manual mode.

`test_guard_enemy.cpp` checks deterministic patrolling, distance activation,
contact damage and cooldown, three authentic projectile hits, wall cover,
bounded life and replay reset. `test_guard_enemy_raster.cpp` verifies that
actual rendered RGBA pixels change with guard presence, awareness, player
damage and death. Both join the existing CTest suites in GitHub Actions.

## Verification limits

The prior seven-event manual controller witness, NeXium ZR dash witness,
normal guest exit, and 200-frame autoplay must continue to pass without
redefining their schemas. The new guard is enabled only upon **manual**
play entry. A new guest-written `guard_witness.txt` records the first
simulation tick at x=257 px and the eighth patrol tick at x=264 px,
with the guard still at health 3 and not yet alerted. The independent
`audit_nexium_guard_guest.py` checks exact event order, values and
provenance, requiring the earlier manual, dash and process-exit audits.
Host-side mutation fixtures are not accepted as emulator proof.

These two records, if observed in the new NeXium Actions run, demonstrate
**actual native guest guard patrol execution**, not native evidence of
enemy pursuit, melee attack, death, or original-game fidelity. Contact
combat is verified independently by host C++ simulation and RGBA tests.
Physical Nintendo Switch performance remains untested.
