# Live fourth-wave hostile projectile halo — independent NeXium proof

This ROM-free homebrew witness tests authored UI illumination, not any
claim of parity with the original Vice: Project Doom NES game.

On the existing **real fourth manual run**, the app first verifies the
third earned stage victory and physical Minus+Right restart, the new
guard's authentic three bullet impacts and activation of wave two.
When the source `Simulation::enemyProjectiles()` contains its first
still-active, on-screen, fourth-run hostile turret projectile,
the NRO records the selected projectile slot and actual fixed-point
x/y/velocity/age and the sentry's real shot count.

On the **same game simulation frame**, the NRO draws the full native
scene with optional hostile halo disabled and samples 32×32 = 1,024
RGBA8888 pixels at the projectile center. It then draws the *same*
state with the halo enabled, measures the same pixels and displays the
illuminated frame. No extra enemy tick, fabricated projectile, host-only
image, altered controller input or physics modification is permitted.

A native SD witness is accepted only if the real wave is active,
the guard is defeated, sentry and hero alive, projectile slot/age/velocity
are valid, the turret really fired and at least 3 distinct pixel values
changed with unequal hashes. Exact actor/sentry pixel colors remain
authentic because the optional halo is composited **before** sprites.

The independent Python auditor must correlate the bullet event frame
to the *same* fourth-run guest wave/exit trace, with preexisting X11
fourth-stage clear, fourth-reset, real hit-light and dust PASS artifacts.
No data from a standalone synthetic host C++ fixture may substitute
for a native guest source record.

The source C++ test verifies genuine second-wave bullet firing,
bounds, stride, sample hashing and rejection of impossible or unchanged
pixels. The Python mutation tests reject counterfeits, wrong counts,
wrong velocity/coordinates and missing independent stage/X11 evidence.

Acceptance requires all Native Core, graphical CTest + NRO build,
Debug/Release, native probe (if triggered), and genuine NeXium guest
workflows, including existing strict live alert-red guard, same-frame
footstep, guard-hit illumination and earned stage completion.

Physical Switch video output, performance and original NES fidelity
remain unproven.
