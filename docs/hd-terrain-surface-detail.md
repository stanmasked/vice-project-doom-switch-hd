# ROM-free HD terrain surface material relief (optional preview)

## Goal

Add restrained, static visual depth to *existing* collision-map ledges
in the original-style 1280×720 **homebrew prototype**, without inventing
game mechanics, moving objects, rewriting art assets, or claiming
restoration of original NES textures.

This is an original authored effect, not recovered original
`Vice: Project Doom` map data or a pixel-for-pixel remaster.

## How it works

`graphics_core/terrain_surface_detail.hpp` reads the same
`SceneView::solid_at` 16px tile callback used by the renderer. It
adds thin top-edge highlights only where the tile above is not solid,
narrow shade on exposed left faces only where the adjacent tile is
not solid, and a few extremely subtle fixed world-coordinate material
marks on uncovered tops.

All computations are integer-only in the existing RGBA8888 pipeline;
the algorithm never advances the source simulation or alters the map,
collision, input, hit-flash timers, actors or the game camera.
World-seeded patterns and lighting bands move with the map during
camera scrolling rather than swimming across the viewport.

## Hard compatibility limits

- `SceneView::hd_terrain_detail` defaults to **false**.
- The graphical Switch frontend enables the flag only for manual
  play and only when no user-supplied external terrain atlas is loaded.
- `drawScene` independently enforces the same restrictions. Custom
  user atlases must never receive this authored overlay.
- The effect draws after solid terrain but **before** exit objects,
  player, enemies, projectiles, effects and HUD. It cannot recolor
  the native guard-alert or hit-flash silhouette used by NeXium audits.
- All ROM-free automatic replay/approved golden frames remain unchanged.
- The renderer clips to the visible framebuffer width, leaves padded
  rows untouched and preserves original RGBA alpha.

## Test coverage

`hd_terrain_surface_world_lock` checks exposed/buried top edges,
external/internal side faces, unchanged alpha/stride padding,
camera shift by one gameplay tile, repeatability, invalid inputs and
negative/extreme camera coordinates.

`hd_terrain_surface_scene_integration` checks
pixel changes in manual mode, pixel identity for autoplay and external
terrain overrides, deterministic full-scene output, original
alert-red guard torso preservation and framebuffer stride padding.

GitHub CI additionally rebuilds the Nintendo Switch graphical NRO
and runs the full NeXium scene/control evidence pipeline before
accepting this stacked branch.

## Dependencies and limitations

This branch is stacked on graphical impact-light PR #42, which depends
on PR #41; all previously confirmed graphics and source-hit evidence
should remain intact. Without extracted, licensed original art, the
new material detail is a restrained original-style rendering preview
only. Physical Switch quality and actual 60-fps throughput remain
unmeasured.
