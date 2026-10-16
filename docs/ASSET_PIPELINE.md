# VPAT v1 — independent HD sprite atlas pipeline

Stage 23 introduces an **author-authored image** import and runtime frame
display layer for the native Nintendo Switch framebuffer renderer. The
original commercial NES ROM, extracted sprites or tile sheets are not
present in this pipeline or its GitHub CI fixtures.

## Binary format (little endian)

Byte offsets:

| Offset | Type | Meaning |
|---:|---|---|
| 0 | 4 bytes | ASCII `VPAT` |
| 4 | u16 | Version = 1 |
| 6 | u16 | Atlas width, pixels |
| 8 | u16 | Atlas height, pixels |
| 10 | u16 | Frame width |
| 12 | u16 | Frame height |
| 14 | u16 | Frame count |
| 16 | u16 | Flags = 0 |
| 18 | u32 | CRC32 of pixel payload |
| 22 | bytes | Width × height × 4 unpremultiplied RGBA8888 pixels |

All frames are **non-overlapping, row-major cells**. Dimensions must be
nonzero, evenly divisible by frame size, and at most 1024 pixels per
atlas axis. Frame count may not exceed available cells. The runtime
rejects unsupported versions, malformed lengths, invalid frames, bad
dimensions and CRC mismatches. It never decodes PNG on the Switch.

C++ consumers call `openAtlas` on an in-memory immutable blob and then
`blitAtlasFrame` to blend a selected frame into a 32-bit RGBA framebuffer.
Alpha 0 is transparent, alpha 255 is opaque; intermediate values use
integer straight-alpha blending. Drawing clips to framebuffer bounds,
accepts scales 1–8 and respects a pixel stride larger than screen width.

## Author a new texture sheet

Any RGBA PNG with uniformly sized grid cells can be converted. For
example, an independently created 4-frame 96×32 texture sheet with
24×32 cells:

```sh
python3 tools/pack_vpat.py private/my_new_hero.png \
  --frame-width 24 --frame-height 32 --frames 4 \
  --binary private/my_new_hero.vpat \
  --header private/generated/my_new_hero.hpp \
  --namespace vpd_art --symbol kAtlasBlob
```

The generated header exposes `vpd_art::kAtlasBlob` and
`vpd_art::kAtlasBytes`; use those with `openAtlas`. Import from
non-proprietary or appropriately licensed **newly authored** art only.
Existing game assets are not redistributable merely because they were
converted.

The current diagnostic builds an entirely **synthetic** atlas from Python
drawing primitives automatically:

```sh
python3 tools/build_demo_atlas.py private/generated/demo_atlas.hpp \
  --raw private/generated/demo_atlas.vpat \
  --preview private/generated/demo_atlas.ppm
```

The generated 96×32 RGBA sheet contains four independent pose sketches:
idle (0), run A (1), run B (2), airborne (3).
The current Switch diagnostic selects frames using `grounded`,
direction-button input and the fixed-tick frame counter. Those animations
and physics are **prototypes**, not original Vice: Project Doom timings.

For the built-in scene, `make -C switch_graphical clean all` automatically
regenerates the C++ header and embeds the resulting VPAT resource inside the
NRO. There is no external runtime asset loading and no dynamic PNG decoder;
hot-reload and filesystem asset streaming are **future work**.

## Reproducibility and validation

```sh
cmake -S graphics_core -B build/graphics_core -DCMAKE_BUILD_TYPE=Release
cmake --build build/graphics_core --parallel
ctest --test-dir build/graphics_core --output-on-failure
python3 -m unittest discover -s tests -p 'test_vpat_packer.py' -v
```

C++ host tests cover malformed header and checksum rejection, clipping,
transparent pixels, drawing into padded framebuffers, and the fact that
idle, running and airborne poses affect the complete rendered scene.
Python tests cover PNG alpha preservation, dimension/frame constraints
and generated C++ identifiers.

The Switch cross-build uses the same `graphics_core/asset_atlas.cpp`
runtime parser, the same `graphics_core/scene_renderer.cpp`, and a
generated compile-time resource header. It does **not** establish that
frame rate or art quality is adequate on physical Switch hardware.

## Next

Replace the synthetic frames with independently painted high-definition
hero animations, expand a metadata manifest for frame duration and action
states, and check display performance on physical Switch hardware.
Reconstructing authentic first-stage palette, geometry and behavior
from locally observed reference traces remains an independent unresolved
research task.

## Stage 24 — animation metadata separated from VPAT

An independently authored JSON clip manifest (currently
[demo_animation.json](../assets/demo_animation.json)) maps logical animation
states to VPAT frame IDs and integer simulation-tick durations. It is
compiled to constexpr C++ before the NRO build via
[build_animation_manifest.py](../tools/build_animation_manifest.py).
No dynamic JSON parsing or allocation is required during gameplay.

The portable [AnimationPlayer](../graphics_core/animation.hpp) handles
state changes and looping without modifying sprite texture encoding.
See [ANIMATION_CONTROLLER.md](ANIMATION_CONTROLLER.md) for the schema,
safety checks and tests. All current frame durations are placeholders.
