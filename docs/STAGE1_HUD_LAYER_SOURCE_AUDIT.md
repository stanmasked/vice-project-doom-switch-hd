# Stage 159 — isolate the Stage 1-1 bottom HUD from the road

## Original-game observation, not a Switch implementation claim

Real owner-private USA Vice: Project Doom ROM+read-only FM2 captures in
FCEUX 2.6.5 were compared at original movie frames **600** and **800**.
The unmodified scene images show an overhead driving scene
above a separate bottom **score/time/stage/status HUD**. This observation
alone does not establish the road's scrolling speed.
At these particular screenshot frames, the manual image-space boundary
between those visible areas is approximately **Y=196** in the original
**256×240** framebuffer. Treat it as a **visual analysis/renderer
separation boundary**, not a proven NES raster write scanline.

Previously verified one-instruction counterfactuals used:
- MMC3 CHR register **#0** writer at CPU **$E380**, replacing X=00 with
  X=02 for one target frame, and returning X to 00 at $E383.
- PPUMASK writer at CPU **$E38E**, replacing A=0E with A=06, and returning
  A to 0E before $E391 RTS.
- A separate MMC3 CHR register **#1** substitution at $E387 from 02 to 00,
  which did **not** produce visible pixels in the observed four-frame windows.

Both positive interventions altered only screenshot **N+1**. The RGB
per-pixel difference mask matches the indexed NES palette difference mask
exactly in every compared original frame. All screenshot pixels in the
putative road region **Y=0–195** were identical across both control/probe
pairs, whereas changed pixels were confined to the bottom HUD region
**Y=196–239**.

## Measured counterfactual spatial overlap

| Original probe target | CHR #0 changed px | PPUMASK changed px | Changed by both | CHR #0 only | PPUMASK only | Mask IoU |
|---:|---:|---:|---:|---:|---:|---:|
| 600 (screenshots 601) | 3,042 | 1,607 | 1,199 | 1,843 | 408 | 0.347536 |
| 800 (screenshots 801) | 3,039 | 1,619 | 1,205 | 1,834 | 414 | 0.348972 |

CHR #0 changes original framebuffer rows **196–207, 209–223, 228–231,
236–239**. PPUMASK changes rows **201–207, 209–223**. Thus the selected
CHR #0 intervention also affects HUD-only extra rows **196–200, 228–231,
236–239**, which the PPUMASK probe does not affect.

Changed-pixel spatial masks are highly consistent between the two
independent samples:
- CHR #0: intersection **3,005** / union **3,076**, IoU **0.976918**.
- PPUMASK: intersection **1,577** / union **1,649**, IoU **0.956337**.

These facts support **separating a HUD rendering layer from the overhead
road/cars layer** when developing a ROM-free original-style HD Switch
prototype. They do **not** establish sprite CHR semantics throughout
gameplay, prove a particular PPU scanline/dot of $E380/$E38E execution, or
recover original road scroll/camera speed or vehicle physics.

## Source-only audit and safeguards

Run the following code against owner-private original/probe capture paths:

- tools/audit_private_stage1_hud_graphics.py
- tests/test_audit_private_stage1_hud_graphics.py

The script accepts a private JSON manifest sorted by frame, with
**two to eight** entries, each containing the keys:
- frame: integer original FM2 frame index
- original: absolute private original capture directory
- chr0: absolute legacy private CHR #0 intervention capture directory
- ppumask: absolute private PPUMASK intervention capture directory

The program deliberately requires the explicit
**--acknowledge-legacy-witness** switch. This is because the original
Stage-158 control and intervention captures used different completion
schemas, and the **old CHR #0 witness incorrectly named an actual X
restoration an A restoration**. The private original research script
asserted CPU X restoration, but those old witness **bytes cannot
independently attest X restoration or cryptographically cross-check
the ROM identity** across the different schema formats. Do not rewrite
or silently "correct" a real original witness.

Example invocation (only with paths on your local private workstation):

    python3 tools/audit_private_stage1_hud_graphics.py \
      /private/stage159_manifest.json \
      --acknowledge-legacy-witness \
      --hud-start-y 196 --output /private/stage159_numeric_report.json

Every target requires exact four-frame 256×240 P6 RGB and 8-bit palette
arrays, zero differences outside frame N+1, matching RGB/palette spatial
masks, image-space changes only below the caller's explicitly supplied
HUD start, and independent private capture directories. It returns
only numeric counts, changed row numbers and per-frame IoU: **no
copyrighted pixels or private file paths**. The test suite generates
invented pixel arrays; no original ROM/FM2/screenshots are committed.

A source-free aggregate numerical report is available privately as
vice_project_doom_stage159_hud_overlap_report.json; that report was
independently recomputed from the actual original private images.

## Next Switch-oriented work (not yet done)

1. Build an isolated original-style HD **overhead road/traffic scene** and
   separate bottom HUD layer, with verified clipping between both.
2. Model the gameplay HUD counters and status in source-only code first;
   original font/tiles remain private and should only enter local builds
   with owner assets.
3. Determine actual road motion from separate PPU/CHR and frame-aligned
   evidence **above Y=195**. The current positive CHR/PPUMASK experiment
   constrains **HUD graphics**, not driving camera scroll.
4. Keep Stage 1-1 geometry, vehicle physics, collisions and the 41-frame
   exit blackout as independent testable contracts; no complete original
   gameplay recreation is claimed yet.


## Stage 160 — opt-in ROM-free Switch renderer integration

Implemented an independent source-only graphical preview in
`graphics_core/driving_preview.hpp`. It draws procedural road geometry,
moving marker stripes and a test car *only* above Y=588 at 1280×720.
The HUD background, counters, and health bars are drawn *only* at or
below Y=588. The 588px boundary is the 3× vertical mapping of the
private original screenshot's manually observed 196px split; it is
**not** a measured PPU dot or scanline transition.

`graphics_core/scene_renderer.cpp` selects the separate preview
only when the new `SceneView.driving_stage_preview` flag is set.
`switch_graphical/source/main.cpp` offers a **manual-only
ZL+ZR+X** opt-in toggle, disabled for the original ROM-free synthetic
autoplay; neither original game ROM/FM2 nor its image data are added.
The preview is a visual prototype only and deliberately consumes the
current simulation frame and health without changing collision,
vehicle mechanics, transition states, or default rendering.

CTest target `vpd_driving_preview_test` asserts that road stripe
phase affects only the upper region, status counters only the HUD,
car sprite only the road, padded framebuffer columns remain untouched,
repeated draws are deterministic, and disabling `SceneView` preview
restores the unmodified default scene pixels.

**Next:** replace invented placeholder positions with measured
original gameplay geometry and implement a distinct driving
simulation under separate tests. Authentic road scroll/camera
velocity, traffic collision/physics and gameplay stage-exit remain
unverified, as does original bitmap appearance in this preview.
