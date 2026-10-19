# Native NeXium verification of the ROM-free second wave

PR #24 introduced the gated two-enemy corridor, in portable C++ and
libnx's shared renderer: first defeat the close-range guard, cross the
progression threshold, survive the stationary ranged turret, destroy it
with two projectile hits and reach the far exit. Those host simulations,
raster tests, native builds, and the *previous* live NeXium guard test
passed, but the original host input script did not enter the later area.

This new stacked research phase executes the **same production
Simulation physics inside the real native Switch NRO**, using a separate
bounded offscreen scripted diagnostic at manual game tick 8. It writes a
fresh `second_wave_witness.txt` into its own guest SD filesystem. Unlike
manual gameplay, the script's inputs are authored in the NRO and do not
come from `padGetButtons()`. It does not modify the visible first-guard
battle, camera, HUD, 200-frame demo or prior guest-control witnesses.

Five guest-source events are written from actual simulation fields:

1. `guard`: three real bullets defeat the first guard before activation.
2. `wave`: the living hero crosses the second-wave threshold and the
   two-HP turret becomes active.
3. `hostile_hit`: an independent stationary-player variation receives
   at least one true enemy projectile hit, lowering hero HP.
4. `turret_down`: another independent progression run fires enough
   real swept bullets to remove both sentry health points.
5. `exit`: the hero survives and reaches the checkpoint at tile x=55.

`tools/audit_nexium_second_wave.py` checks exact schema and event
order, source and scenario labels, bounded frames, health and shot
counters, condition transitions and position gates. It requires all
older independent guest evidence: manual controls, ZR dash, first-guard
patrol/live kill and X11 visual disappearance, plus native process exit.
Parser mutation tests cannot replace the real NeXium evidence.
A host C++ test independently repeats the entire five-event script and
checks deterministic equality and its exact guest writer.

A **successful** run proves the new ranged battle calculations execute
in AArch64 guest code and preserve all previous manually controlled
first-guard behavior. It still does **not** prove that a human or
emulated controller actually navigated the second-wave encounter or
that the synthetic stage matches the original NES Vice: Project Doom.
Physical Nintendo Switch execution and FPS remain untested.
