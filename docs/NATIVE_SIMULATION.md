# ROM-free deterministic native simulation (experimental scaffold)

This original test scene establishes controller input, fixed-tick logic, collision
constraints, deterministic replay, and Switch-native executable development.

**It does not reproduce Vice: Project Doom's original physics, stage geometry,
protagonist graphics, attacks, enemies, or timing yet.** It is not an emulator.
No proprietary ROM or extracted game assets are bundled.

## Implementation

- One simulation step per call to tick(); provisional target 60 steps/second.
- Position and velocity use signed fixed point, 1/256 pixel (no floating point).
- Original test scene is 64 by 15 solid tiles, 16 x 16 px each.
- Actor box is 12 x 14 px (placeholder, not an extracted bounding box).
- Placeholder movement: 2 px/frame horizontal; -5 px/frame initial jump;
  +54/256 px/frame^2 gravity capped at +5 px/frame fall.
- Per-axis stepped collision and tile-boundary snapping; jump edge detection.
- Side-scrolling camera tracks the player in a 40-tile viewport.
- FNV-1a replay fingerprint has an explicitly defined byte order.

## Tests

```sh
cmake -S game_core -B build/game_core -DCMAKE_BUILD_TYPE=Release
cmake --build build/game_core --parallel
ctest --test-dir build/game_core --output-on-failure
```

The C++ test checks a 300-frame replay against a golden hash,
reset, jumping/landing, wall collision, held-jump suppression, camera scrolling,
and standing stability. GitHub Actions runs it in both Debug and Release.

## Switch prototype

The libnx `switch_probe` executable presents an ASCII diagnostic scene and
player marker. D-pad/left stick moves; A/B jumps; Plus exits. It has a
~16.67ms sleep and updates its ASCII screen every two simulation frames.
Neither 60 FPS nor input latency is measured/validated on hardware.

## Next

Measure reference behavior from a lawfully obtained ROM locally, then replace
provisional constants and collision behavior with documented, repeatable
measurements. Private ROM dumps and original artwork remain outside GitHub.
