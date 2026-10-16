# Stage 29 — two independent parallax backgrounds (ROM-free diagnostic)

The native Switch test scene now supports a separate **two-frame VPAT**
containing its distant and near background layers. It is an independent,
newly drawn background resource—not scenery extracted from Vice: Project
Doom. The original NES first stage remains unreconstructed.

## Rendering model

The program draws, back to front:

1. Original procedural gradient, stars and moon (no external dependencies).
2. **Far** atlas frame 0, repeated horizontally; slow 1/5 camera-speed.
3. **Near** atlas frame 1, repeated horizontally; 1/2 camera-speed.
4. The independently authored 32×32 terrain VPAT tiles.
5. The hero VPAT/VANM sprite animation.
6. The HUD and independent asset-source indicators.

The optional atlas **replaces only the old procedural skyline**. When no
atlas was supplied in the portable render test, the earlier skyline
remains as a fallback. A failed external backdrop reload keeps the last
validated background atlas active. Sky/terrain/hero are never replaced by
background pixels out of order.

Both layers are authored as independent **alpha RGBA** images in a
two-frame VPAT sheet. The art is tiled every 512 *screen* pixels.
Each image renders at exactly 512×384 regardless of source sampling
resolution. Valid per-frame source sizes are:

| Each frame's pixels | Display scale |
|---|---:|
| 64×48 | 8× |
| 128×96 | 4× |
| 256×192 | 2× |
| 512×384 | 1× |

All four sizes obey VPAT v1's maximum 1024-pixel atlas-axis constraint
when arranged horizontally as two frames. Other atlas arrangements may
work if the VPAT header is valid and the logical cell size qualifies.
The built-in independent example uses **128×96**, two layers, and
transparency above each skyline. Runtime conversions are nearest-neighbor,
not artistic upscaling.

The parallax offsets use *logical camera pixels* and are floor-rounded
for negative positions. The two speeds are author-selected diagnostics,
**not** measured from the NES game. The layer draw calls clip safely at
screen edges. The background does not change gameplay physics, collisions
or sprite animations.

## Updating an independently authored background

The additional optional file is:

    sdmc:/switch/vice_project_doom/backdrop.vpat

Put it beside the earlier asset files:

    switch/
      vice_project_doom/
        vpd_native_scene.nro
        hero.vpat          optional character sprite
        hero.vanm          optional character timing
        terrain.vpat       optional terrain tiles
        backdrop.vpat      optional two-layer parallax art

Controls:

| Button | Action |
|---|---|
| **L** | Reload backdrop.vpat only |
| **R** | Reset backdrop to the built-in resource |
| **ZL / ZR** | Reload / reset terrain |
| **X / Y** | Reload / reset hero and animation |
| D-pad / left stick | Move test character |
| A / B | Jump |
| Plus | Exit |

The HUD reports **BG: SD**, **BG: EMBEDDED**, or **BG: FAILED**.
A failed manual reload does not erase an earlier valid backdrop.
There is **no cross-resource atomicity** across background, terrain and
hero groups. They are deliberately independent for artist iteration.

## Import a new two-layer PNG

Example: an original **512×192** PNG with two 256×192 RGBA frames:

~~~sh
python3 tools/pack_vpat.py private/backdrop_editable.png \
  --frame-width 256 --frame-height 192 --frames 2 \
  --binary private/backdrop.vpat
~~~

The source must be newly created / appropriately licensed. Transfer
the output to the SD path and press **L**. Transparency in the PNG
becomes transparency in the atlas and may reveal the existing sky.

To regenerate the smaller synthetic embedded art:

~~~sh
python3 tools/build_demo_backdrop.py private/generated/demo_backdrop.hpp \
  --raw private/generated/demo_backdrop.vpat \
  --preview private/generated/demo_backdrop.ppm
~~~

This Python generator has no Pillow dependency, so it works inside
devkitPro's native NRO build container.

## Verified and remaining work

ROM-free tests check two distinct generated silhouettes, transparent
sky, VPAT byte count/CRC, negative/positive parallax offsets,
framebuffer changes as camera position changes, corrupted/wrong-frame
file rejection, unsupported geometry, and reload rollback. A separate
devkitPro CI job links the **same portable C++ code** into a Switch NRO.

Nothing here proves a physical Switch executes the NRO at acceptable
frame rates; the software renderer is not yet profiled on hardware.
No original Vice: Project Doom level layout, background art, palettes,
AI or timing has been reconstructed. These tests demonstrate a usable
**graphics infrastructure**, not a completed or faithful HD remaster.
