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

## Stage 29 — independently reloadable background

The diagnostic now uses a separate two-frame alpha VPAT background:
far skyline (1/5 camera-speed) and near skyline (1/2 camera-speed).
Put a matching resource at `sdmc:/switch/vice_project_doom/backdrop.vpat`.
Press **L** to load the new background and **R** to restore the built-in
test art. Controls X/Y (hero) and ZL/ZR (terrain) are unchanged.
An invalid background keeps the last valid one.

Details: [PARALLAX_BACKGROUNDS.md](../docs/PARALLAX_BACKGROUNDS.md).
The original NES first-level background has not been extracted, and
background quality/performance has not been tested on physical Switch.

## Stage 30 — animated decorative objects

The synthetic scene includes an independent four-frame alpha VPAT
for a signal lamp (bright/dim) and a ventilation fan (two poses).
These are **visual only** objects with no collision effect. Positions are
anchored in test-scene world coordinates and backgrounds/foregrounds
are composited on opposite sides of the hero/terrain layers.

The optional SD resource is
`sdmc:/switch/vice_project_doom/decor.vpat`. Use **D-pad Up** to
reload it and **D-pad Down** to return to the embedded art; all prior
X/Y, L/R and ZL/ZR art controls remain the same. The last valid decor
resource is retained after a failed reload.

See [DECOR_EFFECTS.md](../docs/DECOR_EFFECTS.md) for authoring, the
supported sprite sizes, scene ordering, automated tests, and boundaries.
The graphics and effects are placeholders, not faithfully restored
original NES game content.

## Stage 31 — reload placement data separately from decoration art

Object placements now come from a VLAY v1 resource. Editing a JSON layout
and rebuilding only decor_layout.vlay lets you change world positions,
rear/front layers, frame IDs and animation tick durations without
recompiling the NRO or changing decor.vpat.

Optional SD resource: sdmc:/switch/vice_project_doom/decor_layout.vlay
Minus reloads this file, and a right-stick press (R3) restores defaults.
Up/Down remain dedicated to the decoration image atlas.

Read docs/LEVEL_PLACEMENTS.md for the binary schema and safety rules.
These positions are diagnostic fixtures, not reconstructed original map data.


## Stage 160 — opt-in driving/HUD visual preview

The graphical Switch NRO now includes a **ROM-free overhead driving-stage
preview**. First leave autoplay for manual play using the left-stick click
(the existing control); then press **ZL + ZR + X** together to toggle the
preview on/off. The same chord consumes the X atlas reload and ZL terrain
reload on that activation, and no extra dash command is submitted from
the toggle. Returning to autoplay resets preview selection.

The driving preview has a strict, unchanging original-framebuffer-inspired
HUD split: the observed NES image-space line **Y=196/240** maps to output
**Y=588/720**. Drawing in the road layer is hard-clipped above output
row 588, while the HUD is hard-clipped to rows 588–719. The road area
uses invented test road markings and an invented car sprite; the HUD
contains independent numeric status/HP bars. Source ROM, NES tiles, game
screenshots, FM2 and copyrighted HUD lettering are **not included**.

The preview receives the pre-existing simulation's current frame and
health **for visualization only**. It does not implement vehicle physics,
road collision, authentic gameplay or original camera speed. The
pre-existing platform renderer, golden synthetic replay frame and
manual combat scene are unchanged by default. Test coverage:
`tests/test_driving_preview.cpp`, registered as
`romfree_driving_preview_hud_road_isolation` in graphics_core CTest.
It verifies layer independence, padded framebuffer bounds, deterministic
redraw, source viewport boundary and reversion to the old SceneView path.

Research provenance: `docs/STAGE1_HUD_LAYER_SOURCE_AUDIT.md`.


## Stage 161 — independent playable driving prototype controls

The opt-in ROM-free overhead driving preview now uses a **separate,
deterministic test-only vehicle controller**, `game_core/driving_simulation.hpp`,
instead of copying the platformer's running-frame and hit-point values.
Enter manual mode with StickL, then toggle this driving preview with
**ZL+ZR+X**. While the preview is selected:

- **Left/right or left stick** steers the invented test car, constrained
  within the invented road bounds.
- **Up or A** accelerates. **Down or B** brakes (brake takes priority
  when both are held). Maximum and acceleration values are diagnostic,
  not source-game measurements.
- A **synthetic traffic obstacle** progresses down the separate road
  layer. Invented AABB contact lowers the preview health bar with a
  45-update invulnerability cooldown and temporary visual flash.
- An independent status HUD displays prototype time/frame, speed and
  vehicle health. Road pixels are hard-clipped to rows 0–587; HUD pixels
  are hard-clipped to 588–719 at 1280×720. No original copyrighted
  background/tile/car artwork is embedded.

During this mode the original **platform `Simulation` is paused**:
its `game.tick()` is not invoked, and the current vehicle update
does not modify platform enemies, projectiles, game-map collision or
existing stage completion. Leaving the preview restores the normal
platform renderer and resumes its prior state; entering the preview
again starts a fresh diagnostic car fixture.

Native CTest coverage in `tests/test_driving_simulation.cpp` checks
steering and speed limits, collision cooldown, deterministic replay,
health clamping and reset. `tests/test_driving_preview.cpp` additionally
verifies the input-driven vehicle snapshot draws only to the road
while independent health/speed counters draw only to the HUD and the
legacy platform framebuffer remains unchanged after toggling.

This is NOT the original Vice: Project Doom Stage 1-1 vehicle physics,
camera scroll, road geometry or source graphical content. The next
development stage must derive those properties independently from
private original-game evidence before calling them authentic.


## Stage 162 — shared driving-state-to-raster adapter (synthetic only)

`graphics_core/driving_scene_bridge.hpp` is now the single mapping from a
`DrivingState` tick to the `DrivingPreviewView` that libnx renders. It covers
position, scrolling, frame counter, independent HP/speed, obstacle and impact
flash; no hidden platform `Simulation` fields are read. This removes the
duplicated NRO-side assignment sequence that could silently drift away from
native tests.

The new `romfree_driving_scene_bridge` CTest checks that all adapter fields
track the same invented physics state, that an actual simulated collision
updates the HUD without altering roadway pixels when only HP changes, that
`drawScene` selects exactly the direct driving preview when enabled, and that
the old platform framebuffer/fingerprint are unchanged after returning.

This is **host-side source integration coverage**, not a claim of a successful
NeXium guest controller run or calibrated original NES car behavior. No ROM,
FM2, screenshots, graphics captures, or licensed assets are included.
## Stage 163 — live-driving guest proof (pending NeXium validation)

Manual mode is still entered with StickL or R+A. Driving toggles only
with ZL+ZR+X (the NeXium default keyboard keys R+T+V).
The native five-event trace records genuine input-driven entry,
right/throttle, left/brake, a one-point car collision, and exit, together
with the *unchanged* platform Simulation fingerprint.
No NES ROM, FM2, CHR or original artwork is committed. Host controls
alone cannot satisfy the native state-machine proof.
A separate second NeXium launch in the runtime workflow tests this exact
chord, both steering directions, accelerator/brake, a 5-to-4 HP collision,
and the return to the original platform rendering. The auditor requires
five ordered native guest records and four different actual X11 P6 frames.
This is a gated real-emulator test: merely adding the script does not
establish that the emulator passed it.
## Stage 164 — source frame raster/health witness (synthetic art only)

For native pad-driven events 2 (steer+throttle) and 4 (real synthetic
collision), the NRO now samples its OWN final `drawScene` buffer before
`framebufferEnd`: the car body pixel at `(car_x,450)` and the fifth
health pip at `(535,648)`. Both are validated against source-defined RGBA
colors and source flash phase. A second independent Python auditor joins
each sample to the exact native physics frame and refuses incomplete or
inconsistent records. This is additional proof of synthetic preview wiring,
not of original NES sprites or Switch hardware output.
