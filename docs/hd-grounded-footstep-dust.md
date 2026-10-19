# Manual gameplay: grounded movement dust

Optional, original-authored ROM-free visual feedback, stacked on the
validated nocturnal haze from PR #44. This **does not** reproduce extracted
Vice: Project Doom animation or proprietary art.

The manually controlled Switch prototype exposes
`SceneView::hd_footstep_dust=true`, while the renderer defaults it to
false, preserving old callers and autoplay golden frames.

Dust appears **only when all source predicates are true**:

- visible manual gameplay (never the scripted attract mode);
- player is both `moving` and `grounded`;
- positive player health and an uncleared stage.

The tiny four-particle trail follows the rendered player foot position
and orientation. Its shape is a deterministic function of
`view.frame % 10` and existing state; it adds no timers, random state,
colliders, physics changes or heap allocation.

Particles render before live hero/guard/sentry silhouettes. Thus
their official RGB values remain available for the strict NeXium
guard-alert and source-hit visual audits. No game-core files change.

The regression in `tests/test_scene_renderer.cpp` asserts an actual
visible difference for grounded moving characters, deterministic
repeatability, unchanged stride padding, and exact no-op identity
when stationary, airborne, defeated or in attract mode.

Do not mark this PR Ready until Native Core, graphics CTest, native
NRO build and complete NeXium playback (including prior hit light proof,
fourth-run completion and guard silhouette color audit) are green.
