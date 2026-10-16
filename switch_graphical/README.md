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

## Stage 25 — external SD art override

Optionally put a 4-frame VPAT file at:
`sdmc:/switch/vice_project_doom/hero.vpat`

On launch the program tries this path and falls back to the
compiled-in red developer sprite if missing or invalid. Use **X** to
reload after replacing the file; **Y** to reset to the embedded art.
The HUD displays ART: SD OVERRIDE, ART: EMBEDDED or RELOAD FAILED.

The runtime loader protects against truncated, corrupted, oversized
and frame-count-incompatible files. An unsuccessful reload preserves
the last valid atlas. [Full documentation](../docs/SD_ASSET_OVERRIDE.md).

This feature has only been compiled and host-tested; no runtime test
on a physical Nintendo Switch has been performed.

## Stage 26: external clip manifest

In addition to `hero.vpat`, put `hero.vanm` alongside it to modify
animation frame choices and durations at runtime. The `X` hot-reload
now stages **both** files; bad animation data cannot partially replace
a texture. On a successful reload the animation state is restarted.
`Y` restores embedded sprites and timing. If `hero.vanm` is missing,
stage-25 atlas-only behavior is retained.

A simple ROM-free editor input is `hero_animation.json`. Convert it via:

    python3 tools/pack_animation_binary.py hero_animation.json hero.vanm

See [EXTERNAL_ANIMATION.md](../docs/EXTERNAL_ANIMATION.md). No
physical-console test or original-game timing recovery is claimed.

## Stage 27 — matching the atlas to the animation file

For stronger **accidental content mismatch detection**, create a
VANM **v2** bound to the exact atlas:

    python3 tools/pack_animation_binary.py hero_animation.json hero.vanm --atlas hero.vpat

Reload with X. A v2 animation file for a different same-size atlas
is refused; existing loaded textures/animation remain unchanged.
Previous VANM v1 files continue working but do not provide this check.
For details see [EXTERNAL_ANIMATION.md](../docs/EXTERNAL_ANIMATION.md).

## Stage 28 — independent environment tiles

The embedded graphic scene draws solid platforms with four original,
code-authored tile patterns. This is a *separate* VPAT resource, not part
of the hero's animation bundle.

Put your replacement at `sdmc:/switch/vice_project_doom/terrain.vpat`.
**ZL** revalidates and reloads the ground tiles; **ZR** reverts only
environment artwork to the embedded default. Existing hero **X/Y**
controls are unchanged. A failed ground update preserves the last valid
resource. See [TERRAIN_PIPELINE.md](../docs/TERRAIN_PIPELINE.md).

Tiles must consist of four square cells with sides 4/8/16/32
pixels. Their displayed size is 32×32; changing art does not change
solid world tiles. This scene remains an invented demo, not the authentic
Vice: Project Doom stage.
