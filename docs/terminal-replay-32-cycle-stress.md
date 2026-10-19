# Deterministic terminal replay stress — 32 full encounters

This native-only regression addresses an increasingly important quality
risk in the original ROM-free Nintendo Switch homebrew prototype:
the first few manual replays can pass while a repeated victory or loss
eventually leaves stale world, projectile, physics or enemy state.

## Scenario

The *same* `vpd::Simulation` is reused for **32 terminal encounters**:

- 16 complete manual-equivalent victories: defeat the guard by three
  swept projectile hits, move through the wave gate, defeat the sentry
  with two more genuine impacts and earn the level exit.
- 16 authentic melee defeats: walk into the live guard, take exactly
  five source-side hits until player HP reaches zero.

Win and loss routes alternate. Every iteration requires a real
`retryTerminalEncounter(game, true)`, which invokes the exact same
reset code path used by the Switch NRO's physical Minus input.

## Invariants

1. Minus during a healthy encounter must be ignored and must not
   mutate the replay fingerprint.
2. A terminal outcome must be earned. Minus=false must leave the
   completed/defeated game unchanged.
3. Victory hashes must be exactly identical across all 16 victories,
   regardless of preceding losing attempts.
4. Defeat hashes must be exactly identical across all 16 deaths,
   regardless of preceding victories.
5. After every accepted terminal Minus, the source fingerprint must
   match an independently constructed pristine enemy encounter.
6. Hero HP, position, velocities, flash, guard/sentry HP, attack
   cooldowns and counters, target state, shot/dash state and the full
   bytewise map must all be reset. Every inactive player/enemy bullet
   must also have **zeroed position, velocity and age**, not just
   `active=false`.
7. After the final 32nd reset, normal Right movement and single-shot
   Fire must still work.
8. Once a real victory or melee death occurs, six deliberately aggressive
   ticks of Right+Jump+Fire+Dash must NOT move either actor, create shots,
   advance guard/sentry AI, alter projectiles or modify health/physics.
   Only the terminal screen's outer frame counter may continue advancing,
   until the explicit Minus reset is accepted.

After the 32 standard alternating cycles, an additional **adversarial
earned victory** deliberately changes a distant map tile, triggers a
manual Dash and leaves a player shot in flight. A real source-side
victory and terminal Minus must then restore the original map, clear
all dash/projectile state, and reproduce the exact pristine fingerprint.
This is an extra 33rd terminal reset, not one of the 32 identical-route
replay samples. Its terminal fingerprint is deliberately not compared
to the ordinary unmodified victory hash.

The test emits `VPD_RESTART_STRESS_HOST_PASS` only after all
checks pass and includes a rolling fingerprint-chain checksum for
regression analysis. It runs under CTest alongside the existing
deterministic Debug/Release game-core suite.

## Evidence boundaries

This is **native host-level stress testing** of the independently
authored ROM-free `Simulation`, not proof of a fourth/fifth full
NeXium playthrough, a native Nintendo Switch device or parity with
the NES game `Vice: Project Doom`.

The parent PR #39 still independently requires live guest source,
real keyboard/gamepad events, a genuine NeXium screenshot and
correct fourth-run guard/sentry state before it may be accepted.
