# Manual restart after victory or defeat

The preceding PR #27 added a visible exit portal and clear banner to the
standalone ROM-free Switch homebrew prototype. This phase makes the
two-stage corridor replayable **within the same running NRO**.

## Player input

During normal gameplay Minus retains the existing developer decor-layout
reload function. At either legitimate terminal outcome, Minus becomes
**RETRY**, while Plus still exits the program:

- On defeat (source `playerHealth()==0`), show **MISSION FAILED** with
  Minus: Retry and Plus: Exit. The simulation freezes further movement,
  firing and damage while the player decides.
- On earned stage clear (source `stageCleared()`), the existing
  completion panel now includes **MINUS: REPLAY / PLUS: EXIT**. Likewise
  all mechanics freeze until explicit replay.
- An actual fresh Minus button press calls one shared portable source
  helper `retryTerminalEncounter`. It resets the entire `Simulation`
  and re-enables manual enemy encounters: hero position at tile 3,
  full 5 HP, guard 3 HP, turret 2 HP, inactive wave/exit, zero shots,
  fresh cooldowns and no surviving bullets.
- Minus during active play cannot bypass guard or turret progression;
  the attract-mode demo stays unchanged, including its pinned replay
  hash. Existing guest SD combat attestations remain limited to the
  **first** playthrough, so a fresh replay never forges duplicate
  earlier manual/dash/guard witness events.

## Native NeXium proof

Upstream `nexium-gui/src/controller_config.rs` assigns the default
**N** keyboard key to the Switch **Minus** controller button.
The X11 NeXium driver presses it only *after* the actual guest's live
two-enemy stage-clear event and genuine exit screenshot.
The same NRO emits one canonical `manual_retry_witness.txt` from the
authoritative before/after `Simulation`, never from a script-generated
fixture. It records source victim/winner health, initial and restored
enemy HP, frame counter and the real Minus flag.

The host independently captures the fresh gameplay X11 image. The
fail-closed auditor requires previous seven manual events, actual pad
two-enemy completion, actual native exit code, canonical native reset
fields, independent real host Minus input, and changed full-size
1280x720 PPM/PNG screen images. Damage/complete source fixtures and
RGBA integration tests are additional controls, not substitutes for
guest evidence.

## Limitations

The project remains a self-authored ROM-free training level, not the
original NES Vice: Project Doom. A NeXium run cannot establish real
physical Switch performance or original game fidelity.
