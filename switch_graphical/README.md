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
## Stage 165 — diagnostic driving exit and exact 41-frame blackout

In the manually selected driving preview, press **Minus once** to request
a **test-only** stage exit. The current road frame finishes rendering first.
The next **41 presented native framebuffer frames** are fully opaque black
at 1280x720, and the following frame resumes the prior platform scene.
Driving physics and the legacy platform Simulation are frozen during
the blackout. Minus no longer triggers decor layout reload in this mode.

The 41-frame interval is taken from private original FCEUX frames 3607–3647;
the original 3606→3648 absolute alignment, actual clear condition, original
road geometry, car AI and NES palette data are NOT recreated by this manual
transition. Its full framebuffer/padding/legacy-state contract is exercised
by `romfree_driving_to_platform_blackout`. Genuine NeXium Minus-triggered
runtime evidence remains a separate, unproven step.
## Stage 166 — original-timed diagnostic transition in real NeXium

The independent car preview smoke now uses the real mapped Minus key after
re-entering the driving preview and requires a native sequence of **43**
source-owned guest records: last road, 41 black presentations, and resumed
platform. A separate X11 screen trio is captured at road, midblack and
platform. The audit checks count, sequence, actual framebuffer-black samples,
unchanged platform fingerprint and dark central viewport.

Only the **41-frame interval** is taken from private original FCEUX visual
evidence. The diagnostic Minus control is invented; original game completion,
absolute original-movie frame indices and level geometry remain unverified.
## Stage 167 — numeric original road cross-sections

Seven original Stage 1-1 RGB roadway observations are maintained in
`game_core/driving_road_reference.hpp`, at exact original FM2 frames
only. They must not be mistaken for collision geometry, camera scroll
or vehicle motion. `docs/DRIVING_ROAD_IMAGE_REFERENCE.md` explains
their origin and limitations. No original assets are included.
## Stage 168 — exact-frame road/PPU numerical alignment

`game_core/driving_road_ppu_alignment.hpp` pairs four previously published
original FCEUX movie frames (600,744,800,920) across visible RGB road
cross-sections, an executed source `$2005` write, and a *later* postframe
`RAM $0D` sample. No camera speed, display-effective PPU scroll,
collision geometry or exact raster scanline is inferred.
## Stage 172 — opt-in road image-space measurement swatch

With the **manually selected** ROM-free car preview active, press
**ZL+ZR+Y** once per step to show the seven already documented original
FCEUX roadway *numeric X-interval* examples (600, 744, 760, 784, 800,
840, 920), then OFF. This is a **separate diagnostic** colored strip,
not the original roadway image, NES graphics, physics or raster split.
Its 1280px X coordinates are a simple 5x scaling of source 256px
visible RGB measurements; the overlay's y position is invented and
must not be used as the source measurement scanline. Unobserved
frames are not interpolated or synthesized.

The controlled car, traffic test fixture, simulated road marker speed,
HUD and legacy platform rendering remain exactly as before when this
mode is disabled. Native host CTest validates exact sample width/
edge pixels, padding, HUD and player-car isolation, legacy restoration,
selector gesture authorization, and simulation fingerprint invariance.
A genuine NeXium driving pad gesture test of this *new* swatch is still
a separate pending runtime-evidence gate.
## Stage 173 — genuine native NeXium road-review pixel evidence

The independent second NeXium driving process finishes and retains the
previous five-event car/impact proof and 43-event transition proof **first**.
It then re-enters the ROM-free car preview for a third time, sends eight
actual ZL+ZR+Y pad edges (7 source-numeric intervals, then OFF), and
requires eight libnx-framebuffer SD witness records with real panel/
border pixels, unchanged car/HUD and frozen platform fingerprint.

A separate Python auditor joins the original numeric frame labels to
the source HD interval bounds, verifies pixel samples, no duplicated
controller/guest frame, and compares three actual X11 captures
(first image-space swatch, narrowed source 800, and OFF). Neither
original NES sprites, source scanline scroll, physics or original game
level completion are established by this runtime-only preview test.
## Stage 174 — independent actual X11 road-swatch geometry audit

After the existing Stage173 eight-event native SD witness succeeds,
`audit_nexium_road_x11_shape.py` examines **the three real 1280x720
X11 RGB24 captures** from the SAME NeXium run. It finds pure authored
swatch-fill RGB pixels over four central screen rows and independently
measures the width of source frame 600 versus source frame 800. Source
numerical widths 123 and 56 yield an expected 5x-review swatch ratio
of `(123*5-10)/(56*5-10)`, with a small host display-scale tolerance.

It verifies adjacent authored border/background colors, uninterrupted
fill across multiple actual raster rows, approximately equal centers
for these two samples, and *absence* of the measurement fill on the
eighth OFF frame. It does not assume the NeXium window starts at X=0
or that the source NES image has an independently measured Y boundary.

The three captures remain **experimental NRO screen images**, not
original NES graphics, original ROM screenshots or actual game
collision geometry. Nearest-neighbor RGB colors are intentional;
changes to NeXium filtering/window presentation must be detected,
not silently reinterpreted as authentic original-game road geometry.
## Stage 175 — seven X11 numeric road samples plus OFF

NeXium's independent driving probe captures all **eight** actual X11
RGB24 review frames after the same native guest Y-key edges. The prior
tests and captures are unchanged; extra screenshots are evidence only.

The new `audit_nexium_road_x11_sweep.py` checks seven source-backed
published **numerical** road widths and relative image centers in the
real host X11 raster, plus a blank eighth OFF swatch. It infers one
common host display X scale from wide/narrow intervals but **never**
assumes a desktop window X offset. It confirms equal-width source
frames 600/744 and 840/920, narrowing through 760/784/800, widening
at 840, and measured lateral X shift to 920. Checks do not interpolate
unobserved original movie frames or infer source PPU scroll/camera
velocity, opponent behavior, collision geometry or original NES art.
## Stage 176 — optional source-private 37-frame numeric loader

The cross-platform header `game_core/driving_road_private_bundle.hpp`
and private-only packer `tools/pack_private_road_bundle.py` validate a
164-byte binary with exactly 37 accepted numeric image-space
cross-sections. Four ambiguous frames cannot be selected. The existing
seven-frame Switch diagnostic remains unchanged; this stage prepares
the read-only data format without automatically loading it at launch.
See `docs/PRIVATE_ROAD_BUNDLE.md`. No original game asset is committed.
## Stage 177 — opt-in **37 private** roadway observations in Switch NRO

Place a valid owner-private 164-byte `road_numeric.vprd` in
`sdmc:/switch/vice_project_doom/`. The NRO validates it once at
startup. During the manually entered ROM-free driving preview,
press **ZL+ZR+right-stick click (R3)** repeatedly to cycle all 37 exact
source-numeric image-space cross-sections, then OFF. These are median
RGB **observations**, not road physics or NES screenshots. The
diagnostic strip includes a small `37` marker to distinguish it
from the established built-in seven-sample Y review.

The **ZL+ZR+Y** built-in seven-sample review works with or without the
SD file. The two selectors are mutually exclusive; leaving driving or
switching manual/autoplay resets both. Missing, truncated, corrupted,
wrong-frame or otherwise invalid bundles leave the private 37-selector
disabled without affecting the original game.

The only changed existing R3 behavior is that StickR **does not reset
decorative layout when the driving preview is active**; outside the
preview it continues to work as before. No other guest input, tick,
car collision, camera motion, speed or platform-scene rendering changes.

Host CTest validates all 37 source-only numeric interval pixels and
HID/HUD preservation on a synthetic complete private file. Running
the new selector with the real owner-private bundle inside NeXium
remains a separate required follow-up: public CI provides no original
numeric SD file.
## Stage 178 — isolated NeXium SD startup evidence with invented data

In a separate final NeXium driving process, the CI runner creates a
164-byte **synthetic** VPDROAD1 file at the guest's SD root *before
launch*. The NRO alone reports an SD loader result once on startup:
`VPD_PRIVATE_ROAD_SD_V1`. Its report contains only mounted/loaded,
count and first/last movie labels. The host independently checks the
synthetic CRC and known anchors; no owner-private original numeric
bundle or screenshot enters GitHub or CI.

The preceding full platform/demo, steering/impact, 41-blackout and
seven-frame road X11 proof runs are unaffected. A successful report
establishes only actual NeXium SD read of a synthetic 37-slot
observation file, **not** successful real-pad R3 selection or the
identity of an owner-private ROM/FM2 session. Those require separate
evidence.
