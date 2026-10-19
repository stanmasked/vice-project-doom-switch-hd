# World-space exit marker and stage-clear presentation

This ROM-free gameplay milestone follows PR #26, where the existing
native NeXium input script confirmed a complete run: authentic Right
movement and Y/Fire defeated the guard and ranged sentry, and the hero
reached tile x=55 alive.

Previously this tile-55 requirement was **invisible in the playfield**.
Only a tiny HUD label changed from WAVE 2 to EXIT OPEN and STAGE CLEAR.
Players had no world-space destination marker or positive completion
feedback.

The same host/native source bridge now exposes a synthetic exit at
tile x=55 (world pixel x=880), at the player's grounded world height.
It renders only in explicit manual play after the first-guard victory
unlocks wave two:

- **Locked:** dark doorway with muted red border and LOCK label while
  the ranged sentry is still alive.
- **Open:** brighter cyan-green doorway, an EXIT label and a small
  pulsing beacon only when authentic source `sentry.health==0`.
- **Cleared:** the existing physics `stageCleared()` requires a living
  hero to reach the exit. Once that actually happens, the gate brightens
  and a clear, centrally placed STAGE CLEAR panel states both enemies
  were defeated.

The marker/panel affect rendering only. They do not alter player physics,
enemy HP, game-state fingerprints, demo behavior, level-completion rules
or the native controller witness schema. No original Vice: Project Doom
art, map geometry or ROM content is used.

The new RGBA integration regression derives each stage from real
`Simulation` gameplay: first guard defeat, turret wave activation,
authentic projectile turret defeat and tile-55 level exit. It samples
pixels from the exact shared rasterizer used by libnx, ensures the gate
is hidden in nonmanual/early mode, transitions when the sentry dies,
displays the completion panel only after the earned clear flag, and is
reset cleanly.

Native NeXium checks must still pass on this revision. Its existing
live stage-clear X11 screenshot will now show the destination and
completion panel, but any gameplay claim is limited to the original,
independent ROM-free homebrew prototype and not an authentic NES remake.
