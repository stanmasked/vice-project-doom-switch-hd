# ROM-free manual scene — atmospheric parallax preview

Small original-authored procedural visual enhancement, stacked on the fully
CI/NeXium-verified HD hit-light PR #42. This is **not** restored
Vice: Project Doom artwork, and must not be described as original-game parity.

The opt-in `SceneView::hd_atmospheric_haze` defaults to false. When manual
controls are active, a deterministic and muted five-lane nocturnal sky haze
is drawn into the background after sky/backdrop and before decorative
objects, terrain, enemy sprites, hero and HUD. Position is fixed in world
space with a nine-to-one camera parallax ratio and static integer noise.
No clock/random seed, heap allocations, input state or physics hooks.

The libnx manual scene enables it, while automatic-demo mode cannot draw
it even if the flag is set. Existing manual damage lights are retained,
and existing exact-color red/amber guard sprites are layered above haze.

## Gate

`tests/test_scene_renderer.cpp` tests that:

- replay/autodemo pixels remain identical when the option is toggled;
- enabling the feature during manual play changes real pixels;
- repeating the same render produces the identical RGBA8888 framebuffer;
- padded framebuffer columns are never modified;
- the original golden demo frame, original impact-light tests, live guard
  colors and scripted combat remain unchanged.

Require native graphics CTest, Nintendo Switch NRO, deterministic source
tests and independent NeXium gameplay checks to pass before marking this
new PR ready for review. Actual physical Switch frame-rate impact remains
unmeasured.
