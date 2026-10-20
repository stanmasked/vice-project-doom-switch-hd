# Stage 95 — native source-to-X11 proof of guard melee cooldown refill

The existing synthetic Vice: Project Doom Switch prototype has a living guard
that alerts, hits the hero (5→4 HP) and starts a fixed 32-tick melee
cooldown. Prior stages independently proved the ready `!` at native X11
(PR #67) and three dim pips immediately after the real melee (PR #66).
Their portable renderer test also checks the exact 32→20 progression.
This stage supplies the remaining missing independent **live guest/X11**
evidence for *one pip refilling while the pad is idle at the source-observation tick*.

## Source event (passive, no injected state)

The same physical right-pad first guard contact remains recorded in the
existing guest `guard_live_witness.txt`. After that authentic strike,
the guest stores its actual source frame. Only at **exactly twelve
additional simulation ticks**, with the pad idle at the observation tick
and the
same alerted living guard remains at HP2 with one attack, the hero remains
HP4, HD FX is ON and the actual old cooldown has naturally decreased from
32 to **20**, does it write one source-owned
`VPD_GUARD_COOLDOWN_REFILL_V1` record. The record includes unmodified
`hero_x`, `guard_x`, `camera_x` and both source frame numbers.
The file is truncated before each NRO launch. The recorder neither changes
the timer nor reads commercial ROM assets.

## X11 confirmation

The host keeps the existing first-strike screenshot, releases Right as it
already did, and waits for the new native guest marker. Before it sends the
same ordinary Y/Fire to finish the guard, it captures one extra authentic
full-screen X11 PNG and raw P6 image
`screen-live-guard-refill.png/.ppm`.

The separate fail-closed `audit_nexium_guard_refill_x11.py` requires:

1. All original guard contact, first cooldown-pip, and pre-strike READY
   independent guest/X11 receipts still PASS.
2. The same native strike number and frame plus exactly **12** elapsed
   source frames to `cooldown=20` with unchanged hero HP4 and guard HP2.
   Only the input at the sampled tick is attested as idle; the report
   does not independently attest every intermediate input tick.
3. Full real 1280×720 capture, correct event order, physical pad input
   and a non-duplicated image with original SHA256.
4. Relocation of the real guard by two surviving native HP colors and
   distinctive body/face within the source camera projection.
5. The authored **first warm pip** (RGB 237,170,101) and **two dim pips**
   (92,101,118) in strictly limited sprite-relative regions, with no
   READY exclamation accidentally remaining above the guard.
   Native X11 audit samples three rows within the guard-relative 6×4
   ROIs: in archived real P6 from NeXium #39496177544 the warm pip
   contributes **18**, and each dim pip **15** exact RGB pixels
   at source-anchored guard `(370,559)`. Full displayed rectangles
   extend another row; do not conflate those full sizes with the
   verifier's bounded ROI counts.

Fourteen ROM-free unit tests cover source timing, synthetic/forged health,
non-idle input, duplicate or malformed record, stale frames, detached
cooldown bars, a too-early two-pip refill, invalid native format and a
spurious ready exclamation.

**Acceptance boundary:** do not mark the stacked PR Ready until the exact
head's native Core, deterministic Debug/Release, NRO cross-build and
NeXium complete and an independent
`VPD_NEXIUM_GUARD_COOLDOWN_REFILL_X11_PASS` is emitted. Native source
tick, actual Vulkan output and source screenshots establish prototype
behavior, not Nintendo Switch physical hardware or fidelity to the
copyrighted commercial NES game.
