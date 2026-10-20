# Stage 91 — guard awareness and melee cooldown indicator (ROM-free manual mode)

This stage provides a **useful tactical readability improvement** to the already playable synthetic guard encounter. Unlike the previous stages that tested the hero's low-HP cue, this adds a new optional HUD element **anchored to the enemy in world space**, so the player can tell whether the guard has spotted them and whether another melee strike is ready.

## Gameplay presentation

- Before detection (and after defeat), no marker appears.
- Once the real shared `Simulation::advanceGuard` sets `GuardEnemy.alerted=true`, a compact amber **!** is painted above the living guard while its genuine `attack_cooldown==0`.
- When actual melee contact damages the hero, the source guard sets `attack_cooldown=32`. The exclamation changes into three small pips, refilling as its existing source cooldown counts down. The gauge is purely informational. It does not provide invulnerability or change enemy timing.
- The cue is disabled in automatic demo mode, after player death/stage clear, for a defeated/unaware guard, and when the existing `L+R` HD FX preference is OFF.
- Pixel writes are bounded to **x=(guard_x-camera_x)*2+3..29, y=(guard_y+80)*2-27..-10**, above the source-owned guard sprite. Its torso, guard health cells, five hero health cells, platform collision and exit portal remain unchanged.

## Architecture

- `GuardView.attack_cooldown` is copied from the existing authoritative C++ `GuardEnemy.attack_cooldown` by the *same* `applyCombatOverlay` adapter that Nintendo Switch and host render tests share. No new physics or simulation data.
- `SceneView.hd_guard_threat_tell` is an optional visualization flag set by the frontend's existing HD FX mode and propagated into its zero-extra-tick alternate framebuffer comparison.
- The renderer draws either the amber alert glyph or the cooling pips based on exact source state. It allocates no gameplay state, touches no colliders, and uses no wall clock.
- No NES commercial ROM or game graphics used; this is an authored prototype improvement, not claimed to match the original game.

## Acceptance

The new native host test `tests/test_hd_guard_threat_tell.cpp`:
1. Moves using **genuine Right input** from outside the guard's detection radius until the source AI detects the hero before first contact.
2. Checks the ready **!** appears at the correct pixel coordinates, and only those icon pixels differ from the exact same source frame with HD FX off.
3. Continues through the first **real** melee strike, checks HP5→4 and source cooldown=32, then confirms all three pips are dark immediately after the hit.
4. Waits exactly twelve **idle simulation ticks** for cooldown to reach 20 and verifies precisely one pip lights, with neither simulated HP nor any outside-of-icon pixels altered.
5. Rejects the indicator for a dead/unaware guard, defeated hero, completed level or autoplay demo.
6. Confirms the unchanged source gameplay fingerprint across render-only toggles and the pre-existing attract-mode screen's equality.

The existing graphical CTest suite, Nintendo Switch NRO cross-build, Debug/Release core replay tests and real NeXium end-to-end smoke test must pass on the **exact PR head** before promotion from Draft. A host-only source-to-RGBA test is **not** an independent native X11 proof of this new specific indicator.

The stacked previous PRs #62–64 are Ready for review but not merged.
