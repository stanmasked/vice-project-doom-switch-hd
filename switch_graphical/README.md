# First native Switch graphical scene (ROM-free)

This is a **standalone C++/libnx framebuffer demonstration** using an
independently created city-at-night procedural illustration. It uses the
existing fixed-step test simulation for movement, jumping and collisions.
It is **not** Vice: Project Doom gameplay, original NES artwork, a full
HD remake, or a verified hardware run.

The display is 1280x720 RGBA8888 via libnx's software framebuffer API;
there is no external SDL2 dependency. The background and HUD are generated with C++; the four-frame animated
hero is an independently authored Python-generated RGBA sprite atlas
embedded at compile time. All content is synthetic and ROM-free.

D-pad / left stick moves; A/B jumps; Plus exits. Controller timing and
frame rate require verification on real Switch hardware.

## Host-side raster tests and preview

```sh
cmake -S graphics_core -B build/graphics_core -DCMAKE_BUILD_TYPE=Release
cmake --build build/graphics_core --parallel
ctest --test-dir build/graphics_core --output-on-failure
build/graphics_core/vpd_scene_renderer_test private/scene_preview.ppm
```

## Native NRO (devkitPro/libnx)

```sh
make -C switch_graphical clean all
python3 tests/check_nro.py switch_graphical/vpd_native_scene.nro
```

GitHub Actions performs host tests and cross-builds an NRO from **source
only**, then publishes the ROM-free binary as a diagnostic build artifact.
The native scene and 5x7 pixel font are not derived from game files.

## Stage 23 animated sprite atlas

The `make` target regenerates `generated/demo_atlas.hpp` from
`tools/build_demo_atlas.py` and embeds a versioned VPAT resource in the
native NRO. The game opens it once via `openAtlas` and displays idle,
alternating run poses and airborne pose using the current player state.

To import newly authored PNG sprite sheets, use
[the VPAT PNG converter](../tools/pack_vpat.py) documented in
[ASSET_PIPELINE.md](../docs/ASSET_PIPELINE.md). This build currently uses
a generated **compile-time** asset, not a runtime RomFS loader or
downloaded assets.

```sh
python3 tools/build_demo_atlas.py private/demo_atlas.hpp \
  --raw private/demo.vpat --preview private/demo.ppm
python3 -m unittest discover -s tests -p test_vpat_packer.py -v
```

Embedded sprites are **not** the original Vice: Project Doom sprites,
and the developer animation cadence is not taken from the original game.

## Stage 24 — data-driven animation

The Switch build now compiles two generated source headers:
`generated/demo_atlas.hpp` from independently authored pixel poses and
`generated/demo_animation.hpp` from
[assets/demo_animation.json](../assets/demo_animation.json).

An `AnimationPlayer` runs **once per simulation tick** after movement and
collisions. It selects idle, run, rise or fall, advances by frame durations
specified in the manifest, and preserves facing direction when standing
still or airborne. The renderer only consumes resolved `sprite_frame`
and `facing_left` fields; no JSON parser runs on the Switch.

Tests cover transitions, looping, invalid metadata and a deterministic
200-tick replay through sprite rasterization. See
[ANIMATION_CONTROLLER.md](../docs/ANIMATION_CONTROLLER.md).
