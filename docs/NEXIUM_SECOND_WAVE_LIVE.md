# NeXium: real controller input completes the second wave

This development phase stacks on PR #25's successful native guest-script
second-wave proof. PR #25 verified the new turret and exit physics with a
separate *offscreen* scripted Simulation. That was not the same as actual
manual input. This phase explicitly tests **the same live, visible,
pad-controlled Simulation** in which the first guard was previously
approached, hit and killed with real NeXium X11 keyboard events.

## Actual host/controller flow

The original seven-event manual witness, ZR dash and live first-guard
contact/defeat remain separate prerequisites. The host keeps the *actual*
Right pad key held **continuously** between ZR release and the first
guard strike. This prevents the observed frame-133 race where an idle
`input=0` frame allowed the guard to alert before a later Right
keydown; the independent guest validator still demands a real Right
input on the alert transition. A separate negative regression test
guards this host control continuity without fabricating guest evidence. After the original
guard's confirmed native death and X11 screenshot, the driver keeps the
running game open and holds NeXium's D = Right until the *actual guest*
reports crossing x=26 tiles. Only then does it hold D+Z =
Right+Y/Fire, preventing earlier unverified distant gunfire from
altering the second-wave encounter.

It reads **guest-created** `second_wave_live_witness.txt` to decide when
the scripted *host input trial* has completed and releases the keys only
after a fifth record confirms stage exit. The host does not supply health,
damage, movement, or output traces. Once the guest reported exit, the
host records an additional X11 PNG/PPM screenshot of the visible
cleared stage. This is a distinct experiment from the native offscreen
second-wave script.

`game_core/second_wave_live_witness.hpp` records bounded events directly
after the real pad-driven `game.tick(Input{buttons})`:

1. **wave**: first guard is dead, Right is pressed, player crosses
   x=26 tiles and the turret becomes active.
2. **fire**: actual Y/Fire + Right yields a real source `shotsFired()`
   increase while the turret is alive.
3. **hit1**: one swept player shot reduces turret from 2 to 1 HP.
4. **defeat**: a second swept hit reduces its HP from 1 to 0.
5. **exit**: with health remaining, the same player advances to
   the tile-55 exit and the core reports `stageCleared()`.

A strict independent auditor rejects any missing, reordered, forged or
out-of-bounds events, checks HP/hit conservation, real pad-control flags,
monotonic frames and shots, links first-wave victory before activation,
and requires the previous native manual, dash, first-guard raster,
offscreen turret, kernel-exit proofs, plus the new real X11 screenshot.
Portable C++ and Python regression fixtures exercise source physics
and parser failure cases but are **not** substituted for NeXium proof.

The experiment remains ROM-free and self-authored. Even if all tests
pass, it does not reproduce the actual NES Vice: Project Doom level,
confirm frame pacing, or establish physical Nintendo Switch support.
