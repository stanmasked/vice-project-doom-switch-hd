# Stage 88 — source-owned HP2 warning observed on real NeXium X11

The previous stacked PR adds a purely visual, opt-in manual-mode warning for 1–2 HP. Its native host CTest drives genuine guard contacts and exhaustively ensures that the display does not touch the original HUD heart cells or physics. Stage 88 adds **separate genuine Switch guest/X11 proof**, not another synthetic rendering test.

## Live, untouched second-run source event

After the already confirmed first victory and real Minus, the existing defeat/restart scenario uses an actual physical `Right` pad event until the source gameplay's first guard contact (HP5→4). It then stays idle while the same guard naturally attacks at exactly 32-frame cooldown intervals. A single extra source-owned record is emitted only upon the third actual melee strike, when HP3→2, attacks2→3, first-contact delta equals 64 source ticks, HD visuals remain on, the guard is alive, wave two has not spawned and stage clear is false.

`hd_low_health_guest.txt` is reset on startup, then written by the real libnx simulation tick. No HP injection, synthetic input, independent gameplay script, renderer offscreen substitution or gameplay timing adjustments.

## Native Vulkan/X11

After the HP2 event, the source **also** reports `VPD_HD_LOW_HEALTH_PHASE_V1` at a genuine simulation frame divisible by 24, while the third melee has left HP2 unchanged, no controls are pressed, HD is enabled and the scene is still playable. That is the **start of the real 12-on / 12-off warning's ON half-cycle**. The host waits for this second source marker, then allows X11 to present frames and collects three true native X11 screenshots `screen-live-low-hp-0..2.png/.ppm` inside the ON window, **before** the old guest-owned guard death. Unlike blind short-interval screenshots, this isolates the authored warning phase without manufacturing gameplay states or relaxing pixel checks.

The independently added fail-closed `tools/audit_nexium_hd_low_health.py`:
1. Re-verifies the full old native defeat/retry witness (first contact → later fifth blow/death → fresh Minus), and the independent prior PASS.
2. Requires the third-strike HP3→2 witness exactly 64 ticks after first contact and exactly 64 ticks before death, with an authentic `libnx_tick` source. The additional phase witness must belong to the same third hit and occur on a `frame % 24 == 0` while HP2 is still alive, strictly before the next guard strike.
3. Requires host observation of both source events, all three event-ordered full-resolution X11 PNG+P6 images and at least one image showing **exactly two visible healthy/flashing hearts and three genuinely empty ones**, plus the authored red HP warning underline and `LOW HP` label. The auditor shares the previously independently proven NeXium X11 heart-cell rectangles (`(757..766),(771..781),(786..795),(800..810),(814..824)`, y=17..28) instead of assuming that native window pixels match untransformed authored renderer coordinates.
4. Rejects a fake warning over incorrectly preserved or fake-filled HP slots; original fifth-heart and first-four-heart X11 audits remain unchanged.
5. Writes a separate source-to-X11 PASS report containing image SHA256 and the number of actual warning pixels.

Nine adversarial ROM-free tests reject foreign frames, mismatched source event/cadence, forged guest fields, missing/broken health pixels, missing underline/label and malformed captures.

## Scope and acceptance

- This is a new **native guest X11 verification** for HP2, unlike the previous standalone portable C++ renderer test. It is stricter than simply checking that the source wrote an HP2 record.
- Only an exact-head NeXium run completing **all original scenarios** plus `VPD_NEXIUM_HD_LOW_HEALTH_PASS` confirms the new proof; until then the PR stays Draft.
- The new test adds no commercial NES ROM/files, no claim of original-game behavior, and no claim of verification on physical Switch hardware.

## First exact-head NeXium diagnosis

The initial [failed NeXium run #39471061268](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39471061268) was correctly rejected at the **new** warning X11 gate, even though its source witness explicitly recorded first contact at frame **114**, genuine HP3→2 third strike at frame **178**, and terminal guard death at frame **242**. Archived full native X11 captures had the correct two healthy (yellow-flashed) and three empty cells, but all showed **0 red underline / 0 warning label pixels**. Their timing fell into the warning's OFF half-cycle. The old verifier also used incorrect source-renderer heart rectangle positions, obtaining clipped cell counts (77/66 instead of 120/132). The corrected audit now uses the original native heart rectangles and requires an additional native source-owned ON-phase marker before capturing. The previous run is **not** counted as a PASS; acceptance still requires fresh exact-head NRO/NeXium evidence.
