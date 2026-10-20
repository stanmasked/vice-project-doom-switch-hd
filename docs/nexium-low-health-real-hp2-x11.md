# Stage 88 — source-owned HP2 warning observed on real NeXium X11

The previous stacked PR adds a purely visual, opt-in manual-mode warning for 1–2 HP. Its native host CTest drives genuine guard contacts and exhaustively ensures that the display does not touch the original HUD heart cells or physics. Stage 88 adds **separate genuine Switch guest/X11 proof**, not another synthetic rendering test.

## Live, untouched second-run source event

After the already confirmed first victory and real Minus, the existing defeat/restart scenario uses an actual physical `Right` pad event until the source gameplay's first guard contact (HP5→4). It then stays idle while the same guard naturally attacks at exactly 32-frame cooldown intervals. A single extra source-owned record is emitted only upon the third actual melee strike, when HP3→2, attacks2→3, first-contact delta equals 64 source ticks, HD visuals remain on, the guard is alive, wave two has not spawned and stage clear is false.

`hd_low_health_guest.txt` is reset on startup, then written by the real libnx simulation tick. No HP injection, synthetic input, independent gameplay script, renderer offscreen substitution or gameplay timing adjustments.

## Native Vulkan/X11

After the source event, the host collects three actual X11 root screenshots `screen-live-low-hp-0..2.png/.ppm` during idle pad input, **before** the same old source-owned terminal guard death event. Multiple captures are necessary because the warning deliberately pulses for 12 source frames and remains hidden for the next 12; a single arbitrary screenshot is not proof of a defect.

The independently added fail-closed `tools/audit_nexium_hd_low_health.py`:
1. Re-verifies the full old native defeat/retry witness (first contact → later fifth blow/death → fresh Minus), and the independent prior PASS.
2. Requires the third-strike HP3→2 witness exactly 64 ticks after first contact and exactly 64 ticks before death, with an authentic `libnx_tick` source.
3. Requires a real host observation, all three event-ordered full-resolution X11 PNG+P6 images and at least one image having **exactly two visible healthy/flashing hearts and three genuinely empty ones**, plus the authored red HP warning underline and `LOW HP` label.
4. Rejects a fake warning over incorrectly preserved or fake-filled HP slots; original fifth-heart and first-four-heart X11 audits remain unchanged.
5. Writes a separate source-to-X11 PASS report containing image SHA256 and the number of actual warning pixels.

Nine adversarial ROM-free tests reject foreign frames, mismatched source event/cadence, forged guest fields, missing/broken health pixels, missing underline/label and malformed captures.

## Scope and acceptance

- This is a new **native guest X11 verification** for HP2, unlike the previous standalone portable C++ renderer test. It is stricter than simply checking that the source wrote an HP2 record.
- Only an exact-head NeXium run completing **all original scenarios** plus `VPD_NEXIUM_HD_LOW_HEALTH_PASS` confirms the new proof; until then the PR stays Draft.
- The new test adds no commercial NES ROM/files, no claim of original-game behavior, and no claim of verification on physical Switch hardware.
