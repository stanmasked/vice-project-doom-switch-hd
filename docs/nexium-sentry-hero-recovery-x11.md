# Stage 82: genuine hit-flash expiry with stable hero and health

This ROM-free, stacked NeXium test extends validated **PR #60**. The predecessor proved that a source-owned first turret projectile damaged the idle player, changing HP **5 → 4**, the native X11 fifth health cell, and the actor's two separate hit-only stripes (88 chest and 52 upper pixels).

## Additional source evidence

The graphical libnx NRO now records a **one-line, single-event** `hd_fx_sentry_recover_guest.txt` only if:

- The same real projectile has already been verified by the previous source collision witness.
- **Exactly 16 new Simulation::tick calls** occurred after that collision while all controls were idle and the HD mode remained on.
- The authoritative `playerHitFlashTicks()` transitioned **1 → 0** on that last tick.
- HP remained **4**, the sentry's source hit count remained **1**, the player's fixed-point x/y remained unchanged, both enemy health and fourth-wave conditions stayed stable.

This is an observation of gameplay state. It does **not** change player health, collision rules, visual flash duration or physics.

## Native GUI capture

The host remains idle after the already authenticated hit screenshot. It waits for the fresh recovery SD marker, then allows **180 ms** for Vulkan/X11 presentation before taking `screen-live-sentry-after-recovery.png/.ppm`. The original parent run continues genuine Right+Fire fourth-stage clear and post-clear HD toggle checks.

The independent `tools/audit_nexium_sentry_hero_recovery.py` is fail-closed:

1. Re-verifies the exact native hit record, OFF/ON bullet identity, the existing HUD-hit PASS, the existing actor-flash PASS and the two earlier P6 image SHA-256 values.
2. Requires a **single valid native 16-tick expiry**, HP preserved, hero x/y fixed and source hit count unchanged.
3. Requires the genuine third X11 PNG/P6 and its host-event chronology. The recovered capture must differ in SHA-256 from both earlier captures.
4. Requires **zero** hit-only chest/head flash pixels in the real hero region, the preserved jacket/face silhouette, the **same empty fifth heart** and each of the first four heart cells still intact.

Adversarial Python tests reject early/late expiry, forged source, HP/counter/position changes, lingering flash, missing hero, spontaneously restored health, collateral HUD loss, absent preceding flash and truncated images.

## Acceptance boundary

Until exact-head GitHub Actions run the new NRO through **real NeXium X11** and emit `VPD_NEXIUM_SENTRY_HERO_RECOVERY_PASS` alongside all previous guests' proof markers, the test is not considered verified. The work involves only this independent clean-room prototype; fidelity to the commercial NES release and physical Switch behavior remain unverified.
