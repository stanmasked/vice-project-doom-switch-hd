# Fourth attempt: a second complete replay after the first defeat

## Purpose

After one earned victory, a real source-melee death, a second earned
victory and three manual Minus restarts, the same Nintendo Switch
homebrew NRO must prove that the **fourth** playthrough can itself
defeat both opponents and reach the end of the ROM-free test level.

This phase is dependent on the preceding PR #38's independently
witnessed fourth-run guard death (HP=3→0 via three genuine swept
player projectiles, not an offscreen guest script).

## New source/host contract

- Only after that guard kill, real pad Right must move the visible
  fourth-run actor to the second-wave gate. The native event requires
  an untouched sentry with 2 HP, a living hero, and an uncleared map.
- The actual source game loop then consumes real simultaneous Right
  and Y/Fire, defeats the second-wave sentry by two projectile
  collisions, and records the genuine fourth level-exit state.
- Each of these two source records is uniquely marked as the
  **fourth** stage and written once; previous first/third-run
  records cannot stand in for this one.
- NeXium captures a genuine 1280×720 X11 raster after the fourth
  terminal victory. The auditor requires host key provenance,
  a source-fourth guard kill earlier in the same level,
  valid wave→exit frames, exact sentry hit counters and a
  visible framebuffer difference.
- The portable C++ full-cycle regression continues the fourth
  real Simulation to stage clear and checks negative controls.
  Python mutation tests reject forged order, state, time and origin.

Passing this stage establishes repeatability of our ROM-free
placeholder combat loop. It does **not** recover proprietary NES
stage rules or prove playability of the original Vice: Project Doom
on physical Nintendo Switch hardware.
