# ROM-free run-and-gun shooting prototype

This is an **independent placeholder mechanic**, not a recreation of the
original Vice: Project Doom weapon behavior, timing, damage, sprites or
gameplay. No NES assets or ROM are imported or required.

## Controls

- D-pad / left analog stick: move
- A / B: jump (unchanged)
- **Y: fire** horizontally in the last movement direction
- Plus: exit

On the graphical NRO, the old development-only Y asset-reset action is
moved to **hold left-stick click + press Y**. Reload buttons remain
unchanged.

## Fixed-tick simulation

The shared C++17 game core adds a Fire input bit, a bounded array of
eight projectile slots, a 10-tick repeating cooldown when holding Fire,
six-pixel-per-tick horizontal motion, and a 90-tick maximum lifetime.
Projectiles sweep at most one pixel per collision test, preventing
them from passing through a solid map tile without detection.

Bullets disappear at solid tiles or at end of life. Shooting state
resets with the game and is included in the deterministic FNV replay
fingerprint. The 300-frame **no-fire** golden replay remains unchanged.

The graphical native prototype renders original simple amber shot
rectangles from world-space positions. The ASCII test NRO displays
bullets as asterisks. Both frontends drive the same deterministic
simulation and need no original game resources.

## Regressions

The existing simulation test is extended to verify fixed cooldown,
holding Fire, left-facing shots, collision against a wall, lifetime,
identical per-frame replay hashes and full reset. The scene renderer
test checks that fired bullets change pixels deterministically while
inactive bullets preserve the approved ROM-free golden framebuffer.

Expected host tests:

    cmake -S game_core -B build/game_core
    cmake --build build/game_core
    ctest --test-dir build/game_core --output-on-failure

    cmake -S graphics_core -B build/graphics_core
    cmake --build build/graphics_core
    ctest --test-dir build/graphics_core --output-on-failure

The native Switch NRO must still be built via the existing Switch CI
toolchain and tested on a compatible console/emulator separately.
A build passing CI alone is not evidence of actual Switch gameplay.
