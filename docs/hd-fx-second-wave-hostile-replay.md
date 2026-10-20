# HD effects during the real second-wave hostile projectile

This standalone, ROM-free source-derived regression is stacked on verified
PR #55. It adds no game assets or changes to the Switch controls, physics,
or renderer. The new test is registered in the native graphics CTest suite
with GCC/Clang warnings treated as errors.

## Source-derived scenario

Two independent `vpd::Simulation` instances begin with encounters enabled.
Both receive identical authored controls and are compared by their full
deterministic fingerprints after **every** simulation tick.

1. Three true swept Fire hits defeat the guard, without using mock combat
   views or manually altering enemy health.
2. The player moves through the real wave-two activation gate and into the
   stationary sentry's detection radius.
3. The native sentry itself spawns a genuine hostile bullet. Verify that
   the shot is active, hero/sentry alive and the stage not completed.
4. Isolate **only the hostile-projectile halo** on the actual same-frame
   `SceneView` bridged from the source `Simulation`. Haze, dust, hit light
   and HUD mode indicator are all disabled in both image variants.
   Require different raster hashes in the fixed 414,000-pixel HUD-free ROI.
5. Drive real `HdFxRuntimeMode` L+R OFF, hold for five simulation ticks
   without retoggling, then release and drive L+R ON. The active source
   projectile must persist throughout both edges and no movement, HP,
   AI or projectile state may diverge between simulation instances.
6. Let the projectile continue. Require that an **actual** hostile hit
   decreases player health, increments the sentry shots-hit counter, and
   leaves the two simulation fingerprints and HP identical.

The test also proves the halo does **not** appear in pre-wave frames with
no hostile projectile.

## Acceptance and limitations

The new CTest is `romfree_hd_fx_live_sentry_projectile_replay`. It requires
actual source-driven enemy bullet spawning and an authentic damage collision;
a cosmetic HUD-only color change cannot satisfy it.

This is native *host* gameplay/render proof. Actual libnx L+R on a
**live sentry projectile** has not yet been separately reproduced in NeXium;
the parent PR #55 already established actual libnx L+R during the wounded
guard encounter and once more after victory. Original NES fidelity and
physical Switch execution are not established.
