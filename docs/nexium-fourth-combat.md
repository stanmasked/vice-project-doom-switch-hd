# Fourth manual attempt: real Fire creates a bullet and strikes the guard

This stage stacks on PR #36, in which the same graphical Nintendo
Switch homebrew NRO is manually restarted after a third earned level
victory and an actual Right tick restores gameplay.

## Independent fourth-run combat route

1. NeXium injects Z (Y/Fire) **only after** the native source has
   recorded and visually corroborated fourth-run Right movement.
2. The libnx input loop calls the actual shared `Simulation.tick`;
   native witness #1 requires that a previously unshot fourth-run
   creates exactly one active projectile, with an untouched three-HP
   guard, healthy hero, no dash and an untouched second-wave sentry.
3. X11 releases Z on receiving that source event, allowing the same
   game to simulate the projectile and swept collision.
4. Native witness #2 requires one real guard hit, health **3→2**,
   single shot, and the guard's impact flash, with no other active
   attacks or changed second-wave state.
5. Save a genuine 1280×720 X11 image after that event and compare
   guard-region pixels against the prior fourth-movement screenshot.
6. A fail-closed auditor requires fourth-run prior **PASS**, both
   source SD records, causal frame/x positions, real X11 Fire input,
   guest observed hit and screenshot difference.

The separate portable C++ regression drives the entire win → retry →
loss → retry → second win → retry → fourth Right → Fire → impact
route, rejecting false input and forged damage. Python mutation tests
reject misordered events, missing host evidence, impossible HP/hits and
noncanonical guest records.

**Scope:** The game, enemies, map and assets remain separately authored
ROM-free placeholders. Neither original NES level parity nor physical
Nintendo Switch output is demonstrated by this test.
