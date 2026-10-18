# Native NeXium guest-scripted guard combat verification

This stage stacks on [PR #18](https://github.com/stanmasked/vice-project-doom-switch-hd/pull/18):
the optional, self-authored guard can already patrol in the real libnx NRO,
and its manual-mode first/eighth patrol ticks were confirmed in NeXium.
The new diagnostic extends **guest-executed code coverage** without altering
the already verified on-screen gameplay, original 200-frame attract script
or manually injected right/fire/jump/left/ZR/Plus inputs.

## Two explicitly separate scripted experiments

On frame 8 of manual play, the Switch NRO also runs two *fresh, isolated*
instances of the same portable production `Simulation`. These instances
do not modify or render the live player's battle:

1. **Approach**: continuously supply Right, observe the guard's real
   alert transition when the player enters detection range, and observe
   the first contact attack, which removes one point from hero HP and
   initializes the 32-tick attack cooldown.
2. **Shoot**: hold Fire, advance the existing swept projectile system, and
   observe three distinct impacts lowering guard HP from 3 to 0. Record the
   moment of defeat, when the enemy is no longer alerted.

Source-shared `game_core/guard_combat_probe.hpp` implements the bounded
fixed-step script (at most 210 + 150 ticks) and writes five event snapshots
to `sdmc:/switch/vice_project_doom/guard_combat_witness.txt`.
The NRO truncates that file at startup so old emulator data cannot make
a new run pass. Each snapshot comes from public authoritative game-core
state, not a generated fixture or host-only keyboard log.

The independent `tools/audit_nexium_guard_combat.py` requires exactly five
correctly ordered event rows: alert, attack, first hit, second hit, defeat.
It checks scenario labels, bounded frames, exact HP/hit/attack/cooldown
transitions, canonical numeric formatting and guest-script provenance.
It also requires the prior native manual, dash, patrol and kernel guest-exit
audits to have succeeded. Unit tests mutate and reject individual fields,
orders, sources and missing prerequisites. A host-side C++ replay verifies
that two independent runs of the shared script are deterministic.

## What this does and does not prove

A successful NeXium run proves that the actual **AArch64 NRO executed**
guard detection, melee damage, swept projectile hits and enemy destruction
under a deterministic **separate scripted experiment**. It does **not**
prove that these combat effects were triggered by real NeXium keyboard
input in the visible manual fight. Nor does it establish frame pacing,
physical Switch performance, recovered enemy logic from the NES game,
or any commercial game asset fidelity. The original manual-scene test
and guard's on-screen patrol remain separately verified.

Future work should capture the same health/attack/hit transitions from
the **live rendered manual encounter**, followed by enemies with authentic
behavior only when supported by game-source analysis.
