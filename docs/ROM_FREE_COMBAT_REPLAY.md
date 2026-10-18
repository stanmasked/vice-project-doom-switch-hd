# Deterministic host combat replay (synthetic assets only)

This command makes the currently developed ROM-free Vice: Project Doom
**test-game mechanics** replayable and auditable from a normal desktop
without an NES ROM, emulator or Nintendo Switch SDK. It does **not**
reproduce any original commercial game mechanics.

## Build

    cmake -S game_core -B build/game_core -DCMAKE_BUILD_TYPE=Release
    cmake --build build/game_core --parallel
    ctest --test-dir build/game_core --output-on-failure

Builds the existing deterministic simulation test plus new
\`vpd_combat_replay\`. Three new CTest scenarios exercise the
independent 200-frame proof, its CSV output, and invalid input refusal.

## Host-side proof

    build/game_core/vpd_combat_replay --verify

This runs two *separate* \`Simulation\` instances through the same
authored 200-frame input script. It requires matching fingerprints after
**every frame** and verifies the final state:

| Field | Expected |
| --- | --- |
| Frames | 200 |
| Fired projectiles | 11 |
| Training-target hits | 3 |
| Target health | 0 |
| Complete replay FNV-1a hash | 5947277116621119566 |

It rejects a deliberately changed input at frame 120, verifies a remote
tile-map mutation changes the fingerprint and confirms restoring the
original tile map restores the original fingerprint. The exact final
hash is pinned, rather than accepting two runs that share a newly
introduced deterministic bug. All state derives from independently
written placeholder physics and training art.

Only after these checks may the host binary emit:

    VPD_ROMFREE_COMBAT_REPLAY_PASS

This is **host execution evidence**, not native Switch, emulator or
actual Vice: Project Doom gameplay execution.

## CSV inspection

    build/game_core/vpd_combat_replay --frames 200

Generates one CSV line per simulated frame with a strict header:

\`frame,buttons,x_fixed,y_fixed,camera,shots,target_health,target_hits,active_projectiles,fingerprint\`

Coordinates are fixed-point simulation units (one pixel = 256).
An invalid or out-of-range frame request is rejected; the accepted
period is 1–3600 frames. The final CSV row is pinned by CTest to:

    200,0,12288,53760,0,11,0,3,0,5947277116621119566

The CSV is generated from the simulator; there are no original game
assets or extracted captures. For actual Nintendo Switch testing,
build the independent test-scene NRO in its existing workflow and
test it separately on compatible hardware/emulator.
