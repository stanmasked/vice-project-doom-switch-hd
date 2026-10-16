# Stage 24 — data-driven sprite animation for native Switch

This module advances the ROM-free diagnostic from hardcoded pose selection to
a **fixed-tick, data-driven** animation controller. It is independently
authored, contains **no original Vice: Project Doom sprite timings**, and is
not evidence of authentic gameplay or a validated HD remake.

## Asset and animation sources

- `tools/build_demo_atlas.py` draws four synthetic frames into a VPAT atlas.
- `assets/demo_animation.json` defines the four logical states and frame
  durations in integer **simulation ticks**, not milliseconds.
- `tools/build_animation_manifest.py` validates that manifest and generates
  `demo_animation.hpp` containing static, constexpr C++ clip metadata.
- `graphics_core/animation.cpp` is a portable, allocation-free animation
  controller shared by host regression tests and the libnx build.
- `graphics_core/asset_atlas.cpp` loads the validated VPAT frame data
  and supports nearest-neighbor horizontal flipping to face left.

Example of the *author-invented* manifest structure:

```json
{
  "schema": 1,
  "atlas_frame_count": 4,
  "states": {
    "idle": {"loop": true, "frames": [{"frame": 0, "ticks": 10}]},
    "run": {"loop": true, "frames": [
      {"frame": 1, "ticks": 6}, {"frame": 2, "ticks": 8}
    ]},
    "rise": {"loop": false, "frames": [{"frame": 3, "ticks": 4}]},
    "fall": {"loop": false, "frames": [{"frame": 3, "ticks": 4}]}
  }
}
```

These frames, values and state labels are **prototypes**. The runtime
rejects missing states, unknown properties, zero durations, invalid atlas
frame references and excessive clip lengths; C++ independently checks
the generated bank before display.

## Transition rules

1. Not grounded and vertical velocity negative → **rise**.
2. Not grounded and vertical velocity zero/positive → **fall**.
3. Grounded and horizontal movement active → **run**.
4. Otherwise → **idle**.

Changing states resets clip position. A looping clip cycles its frames
according to their declared tick durations; a non-looping clip stays at
its final frame. The current facing direction updates when horizontal
velocity has a sign and is retained when horizontal velocity is zero.

The controller updates **once per simulation tick**. The rendering
routine receives an explicit resolved frame index and facing flag; it
does not need to understand state transitions. A frame override was added
without removing the procedural fallback used by older diagnostic tests.

For the four-frame synthetic atlas, rise/fall both refer to frame 3
because no separately drawn falling pose exists yet. Future authors
can add one by expanding the independent PNG/VPAT atlas and modifying
the JSON manifest; the animation controller itself does not change.

## Build/test

```sh
python3 tools/build_animation_manifest.py \
  assets/demo_animation.json private/generated/demo_animation.hpp
python3 -m unittest discover -s tests -p test_animation_manifest.py -v

cmake -S graphics_core -B build/graphics_core -DCMAKE_BUILD_TYPE=Release
cmake --build build/graphics_core --parallel
ctest --test-dir build/graphics_core --output-on-failure

make -C switch_graphical clean all
```

C++ regression tests cover valid/invalid metadata, elapsed ticks, running
loops, rise/fall/landing transitions, left/right facing, framebuffer
flipping and a deterministic end-to-end game simulation → clip frame →
sprite atlas → native raster replay. Python validates JSON schema,
frame bounds and generated header data.

The Switch Makefile generates both demo headers automatically before
compiling the diagnostic NRO. The resulting resource remains embedded
at build time; there is **no runtime JSON loader or RomFS streaming**.

## Outstanding work

First-stage geometry, character motion, authentic animation timings,
original visual references, newly painted production HD art, and
performance on real Switch hardware have **not** been validated.
Production timing should follow a measured local original-game trace,
not these temporary synthetic durations. See [ASSET_PIPELINE.md](ASSET_PIPELINE.md).
