# NeXium: genuine playable third attempt after terminal replay

The preceding stack (PR #29 through #31) proves a same-process victory,
first Minus, five melee guard hits causing defeat, **MISSION FAILED**, and
second Minus. The new stage closes the gap between *reset state exists* and
*controls work again after defeat*.

## Source of truth

- NeXium injects a real keyboard **D**, mapped to Nintendo Switch Right,
  **after** the separately captured second-restart frame.
- The live NRO must consume Right in its normal `padUpdate` gameplay loop.
  It records `post_defeat_control_witness.txt` only if an actual tick moves
  the newly reset hero by the source's standard +512 fixed-point units.
- The guest record is further constrained to the third attempt's first 100
  frames, five HP, restored guard and sentry, zero projectiles, no dash, no
  cleared stage, and a minimum +16 px movement since spawn.
- Host releases D after seeing the exact guest-created record and captures
  a **real X11 framebuffer**. The auditor compares the grounded hero's
  visible region against the earlier post-defeat-reset screenshot.
- The new audit also requires the full independent preceding native
  defeat/retry, first-victory-retry and guest-exit PASS results; host strings
  alone cannot satisfy it.

## Falsification cases

Standalone Python fixtures reject forged HP, source, Right, before/after
coordinates, fixed-point delta, frame, guard state and replay progression.
Portable C++ runs the two-terminal scenario and verifies the same writer
rejects idle/fake prior-state data. The emulator itself is the only source
of live keyboard/X11 PASS evidence.

This remains an **original ROM-free homebrew prototype**; it does not prove
the NES game was ported, HD asset parity, original rules or performance on
physical Nintendo Switch hardware.
