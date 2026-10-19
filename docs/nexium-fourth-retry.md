# Fourth attempt after the third earned stage clear

Stages 29–35 establish an original ROM-free homebrew's native control,
first stage victory, earned first Minus retry, real guard-caused death,
second Minus retry, third manual guard and sentry defeat, and a second
earned stage completion. This phase tests that terminal replay does
not become single-use after three increasingly complex attempts.

## New native source evidence

The same live libnx gameplay loop must log exactly two events:

1. **Fourth restart:** a real Switch Minus after the *third-run* guest
   source logged stage exit. The previous state must have an alive hero,
   guard HP 0, sentry HP 0 and clear=true. The source action
   `retryTerminalEncounter` must actually return `AfterVictory`.
   The next state must be frame 0, hero at spawn with 5 HP, guard HP 3,
   sentry HP 2, zero shots, no dashes, and neither a clear nor wave two.
2. **Fourth movement:** after an actual X11 Right key, the same rendered
   game must advance exactly one frame, move the restored player by the
   standard 512 fixed-point units, and remain healthy. This event is
   accepted only after at least 16 pixels of accumulated real movement
   since the fresh spawn.

The host also saves new real X11 frames after restart and movement.
The independent Python auditor requires the existing third-stage
native PASS, live Minus and Right observations, both source events in
canonical order, and pixel changes in the visible hero region.
The portable C++ full-route test compares the newly reset Simulation
fingerprint with a pristine first encounter and rejects spurious Minus,
forged prior positions and movement without Right.

No original game ROM, textures, sounds or Switch firmware are included.
This verifies only the clean-room placeholder scene in experimental
NeXium, not NES gameplay fidelity or physical Switch hardware output.
