# NeXium proof — real footstep visual response

This stacked ROM-free test extends the already CI-passed authored dust
prototype from PR #45. It does **not** claim recovered NES graphics,
measure physical Nintendo Switch timings, or alter authored gameplay.

A real fourth-run Minus → Right controller sequence produces a proven
native `fourth_retry_witness.txt` event. On that exact tick, the NRO
records **1,056 RGBA8888 pixels** in a 48 × 22 area behind the player's
moving heel. It first draws the same scene with dust disabled, then
enables dust and redraws without advancing the simulation, animation or
controller input. It displays the normal dust-enabled result.

A native SD witness is accepted only if all independent source checks
hold: a fresh encounter, alive hero, grounded true, horizontal velocity
+512 fixed-point units, frame 8..100, fourth-run x range, no shots,
no wave, no stage-clear, and at least three genuinely different pixel
values with distinct before/after FNV checksums.

A Python audit requires the witness to match the *exact* `frame` and
`after_x` of `guest-fourth-retry-witness.txt`, alongside the existing
physical Minus/Right, X11 fourth-move screenshot and prior
`VPD_NEXIUM_FOURTH_RETRY_PASS`. Source and onscreen guest provenance
are independent gates; a synthetic host frame cannot satisfy NeXium.

Native C++ unit tests check ROI clipping, stride validity, repeatable
pixel sampling, genuine motion and the failure of invalid states. Python
tests mutate fields, sources, hashes and counts and refuse missing real
controls or X11 context.

This proof is purely visual and uses the same `Simulation` tick as
existing play. It does not alter enemy states, physical collisions,
camera, gameplay timing or legacy auto-demo reference hashes. Original
ROM or commercial graphics are not included.
