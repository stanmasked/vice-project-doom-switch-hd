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
`vpd_combat_replay`. Four additional CTest scenarios exercise the
independent 200-frame proof, its CSV output, invalid input refusal, and independent full-trace audit.

## Host-side proof

    build/game_core/vpd_combat_replay --verify

This runs two *separate* `Simulation` instances through the same
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

`frame,buttons,x_fixed,y_fixed,camera,shots,target_health,target_hits,active_projectiles,fingerprint`

Coordinates are fixed-point simulation units (one pixel = 256).
An invalid or out-of-range frame request is rejected; the accepted
period is 1–3600 frames. The final CSV row is pinned by CTest to:

    200,0,12288,53760,0,11,0,3,0,5947277116621119566

The CSV is generated from the simulator; there are no original game
assets or extracted captures. For actual Nintendo Switch testing,
build the independent test-scene NRO in its existing workflow and
test it separately on compatible hardware/emulator.

## Independent full-frame audit

The host pipeline additionally runs:

    python3 tools/audit_romfree_combat_trace.py \
      --binary build/game_core/vpd_combat_replay

It executes the replay binary with `--frames 200` and independently
checks **all 200 frames** for input schedule, strict increasing frame
numbers, monotonic shot/hit totals, valid health transitions, bounded
active projectiles and canonical CSV values. Four intermediate/final
snapshots are pinned at frames 1, 58, 78 and 200.

The SHA-256 of the entire canonical 200-row CSV, including the header
and line endings, must be:

    488674f6d2a7e506b1187fc4dcc4b28ab1f982fbf401966c661e4b63a0454f19

If one frame's input, position, shot state or fingerprint changes, the
independent auditor rejects the transcript even if the final replay
hash happens to match. Unit tests separately mutate headers, frame
ordering, line endings, counts, numeric encodings and the SHA-256.

The additional acceptance marker is
`VPD_ROMFREE_FULL_COMBAT_TRACE_PASS`; it is **host-side synthetic
evidence only**, never a claim of original NES or Nintendo Switch
runtime fidelity.

## Combat-to-raster integration

The graphical host build now includes:

    cmake -S graphics_core -B build/graphics_core -DCMAKE_BUILD_TYPE=Release
    cmake --build build/graphics_core --parallel
    ctest --test-dir build/graphics_core --output-on-failure

The new `romfree_combat_to_raster_integration` CTest links the **same**
portable C++ `vpd_simulation` used by the Switch source, and the actual
`vpd_scene_renderer` RGBA8888 renderer. It runs the identical
independently authored 200-frame input scenario twice.

At seven selected checkpoints it renders the player, projectiles and
training target using the **same** `graphics_core/combat_scene_bridge.hpp`
adapter called by `switch_graphical/source/main.cpp` before each frame.
A dedicated Python source regression checks that the two consumers
cannot silently return to divergent copy-pasted overlay assignments
and that the Switch Makefile depends on the common header. It
compares deterministic pixel hashes between the two runs and applies
explicit negative rendering controls: hiding the live projectile must
change pixels; hiding the live target must change pixels; restoring
undamaged health marks after the first hit must change pixels; restoring
the target after three confirmed impacts must change pixels.

A successful host test emits:

    VPD_ROMFREE_COMBAT_RASTER_BRIDGE_PASS

This demonstrates **host game simulation-to-raster plumbing only**,
not physical/emulated Switch execution and not original game visuals.
The existing no-shot framebuffer and 300-frame gameplay golden hashes
must remain intact.

## Deterministic combat matrix — 16 scripts, 8,192 frames

The host gameplay CMake additionally builds and runs
`vpd_combat_matrix_test` via `romfree_combat_matrix` CTest.
It executes **16 independently seeded, fixed xorshift32 input scripts**
of 512 frames each, twice, yielding an 8,192-frame test corpus. Every
frame checks identical replay hashes for two independent simulations,
non-increasing target health, no duplicate target hits, bounded bullet
counts/lifetimes, fixed shot velocities and absence of active bullets
inside solid world tiles.

At fixed checkpoints the test also edits a distant world tile and
restores it. An intentionally divergent third simulation must have a
different replay fingerprint until the geometry is restored, then an
identical fingerprint at the restoration checkpoint. This control
asserts that live map bytes participate in replay identity even when
player/shot coordinates are unchanged.

The current ROM-free reference is pinned to:

| Property | Golden value |
| --- | ---: |
| Seed scripts | 16 |
| Frames per script | 512 |
| Total simulated frames | 8,192 |
| Total fired shots | 746 |
| Total target impacts | 44 |
| Combined deterministic 64-bit FNV digest | 6449042941889583905 |

The native **host C++17 mirror** compiled with
`-Wall -Wextra -Wpedantic -Werror` and also with
`-fsanitize=undefined -fno-sanitize-recover=all`. Both passed the
matrix. A local CMake configuration reported 5/5 successful tests after
registering the matrix. These checks are local preflight; GitHub-hosted
Debug/Release CI and Switch NRO execution must be verified separately.
The matrix uses self-authored terrain and training assets only.

A valid host test emits `VPD_ROMFREE_COMBAT_MATRIX_PASS`. Any changed
mechanics must update the golden digest intentionally, after
independent review of the cause and new observed transcript.
