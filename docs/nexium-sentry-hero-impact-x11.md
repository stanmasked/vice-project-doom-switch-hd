# Stage 81 — authentic sentry damage visibly flashes the hero in real NeXium X11

Stacked on **PR #59**, which already validated the same first moving fourth-wave turret projectile, a source-owned swept collision and the loss of only the fifth health cell in the real emulator.

## Observed evidence before writing this check

From the preserved **real run #39455127663**, artifact `vice-nexium-runtime-evidence` #12281470740, we inspected the 1280x720 NeXium PNGs at `screen-live-sentry-hd-fx-on` and `screen-live-sentry-after-hit` and counted actual pixels:

- Authentic source witness: same bullet slot 0; HD ON frame **359**; swept impact frame **396**; HP **5 → 4**, shots_hit **0 → 1**, bullet consumed.
- Upper hero impact stripe: exact RGB **(252,180,119)**, **52** native X11 pixels in x=332..357, y=554..555. The same color was **absent** from the local hero region before damage.
- Hero jacket impact stripe: exact RGB **(255,220,153)**, **88** native X11 pixels in x=335..356, y=574..577. Absent from the same local region in the pre-hit frame.
- Silhouette color **(164,51,68)** persisted at **284** identical X11 pixel positions and face color **(220,179,137)** at **253**, bounding these flashes to the unmoved hero instead of a different world effect.
- A separate HUD test already established 132 changed fifth-health-cell pixels and four remaining health cells; this new check explicitly excludes the HUD from its hero ROI x=300..419, y=538..609.

The native scene renderer already paints both actor-only stripes when `view.player_hit_flash_ticks > 0` from the authoritative `Simulation::tick`; this stage **does not modify** the renderer, collision detection, HP, projectiles, or actor movement.

## Independent CI gate

`tools/audit_nexium_sentry_hero_impact.py` requires the preceding full `VPD_NEXIUM_HD_FX_SENTRY_HIT_PASS`, parses the original source hit and L+R witnesses again, and verifies exact P6 X11 SHA-256 values match the prior collision result. It then checks:

- Exact pixel colors and **both** distinct localized rectangular flashes **only after** actual source damage.
- Precise location and shape of both stripes relative to a stable unchanged jacket and face; prevents false positives from HUD or scenery glow.
- Minimum thresholds that admit the observed 88/52 flashes but reject missing, partial, shifted, pre-existing, or broken shapes.

`tests/test_nexium_sentry_hero_impact.py` includes **eight** synthetic adversarial pixel cases; all eight were executed locally during preparation. CI executes them again before launching NeXium. The runtime script emits `VPD_NEXIUM_SENTRY_HERO_IMPACT_PASS` only after reading the **real** NeXium screenshot pair and live source records; evidence is saved in `sentry-hero-impact-result.txt`.

## Boundary

The actual NeXium rerun on the new exact-head commit must still pass before stage completion. Synthetic tests plus previously recorded X11 measurements are not a substitute for fresh emulator proof. This remains a clean-room ROM-free original prototype; original NES fidelity, physical Switch presentation and frame-perfect timing are not established.

## Live CI race found on first attempt

At first exact-head [NeXium run #39458112786](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39458112786), the guest wrote a fully valid swept source collision at frame 397 (HP 5 to 4), but the X11 root screenshot was taken **before that frame was presented**: the fifth HUD heart was still teal 132/132 pixels, the four other hearts remained teal, and the hero had no flashes. The strict preceding HUD audit correctly rejected this stale raster, so the new hero audit did not execute.

The fix in `tools/nexium_visual_probe.sh` waits **0.18 seconds** after observing the guest SD collision before taking the real X11 `after-hit` screenshot. This is a presentation delay only, not simulated gameplay input or synthetic hit editing. Source flash lifetime is 16 ticks. A new exact-head emulator rerun must confirm the delay suffices.
