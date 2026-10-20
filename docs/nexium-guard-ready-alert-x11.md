# Stage 93 — native READY ! exclamation above a genuinely alerted guard

Ready PR #65 added an opt-in manual-only guard readiness icon and source-driven three-pip attack cooldown gauge. Parent PR #66 independently proved the **three dim pips** are visible on genuine NeXium X11 just after an authentic melee hit, and disappear when the same guard is defeated. Its original source-based 32-tick timer, enemy detection and player health were unchanged.

This stage adds the complementary **native READY !** proof *before* the strike using the SAME real visible gameplay, not an offscreen scripted reenactment.

## True pad sequence

During the existing first manual guard encounter, the host already keeps the actual `D` (Right) button continuously held until the libnx guest writes an independently proven source `guard_live_witness.txt` record for the first alert and later the first strike:

- First alert: native frame **143** in the prior successful run, real Right input, guard `alerted=1`, alive HP **2**, melee cooldown **0**, hero HP **5**.
- First melee strike: native frame **195**, guard attack counter 1, cooldown **32**, player HP **4**.

Host X11 now detects the source-owned **first alert** milestone, leaves the exact same Right input held, gives the actual Vulkan presenter 0.16 s to draw, and records an additional independent PNG + raw full-resolution P6 frame `screen-live-guard-ready`. It then continues the exact pre-existing live strike and first-guard bullet-defeat trajectory. No game ticks are invented, no keyboard change, and the gameplay/renderer implementation remains unchanged in this PR.

## Source- and sprite-anchored exact RGB auditor

`tools/audit_nexium_guard_ready_x11.py` fails closed unless the prior strict guard contact, real strike/defeat pixels, and new independently validated cooldown pips are already PASS. It validates the original guest alert event's real HP, attack cooldown and physical Right input. It computes the guest projected camera location from native source coordinates and independently finds the actual guard torso, face and two surviving HP bars in the earlier X11 image. Only then does it accept both parts of the authored alert exclamation in the proper relative rectangle above that same enemy:

- Alert stem: original amber RGB **(248,198,104)**, at least **50** exact pixels from the native X11 five-by-eleven presentation region (55 if fully visible).
- Alert dot: same RGB, at least **13** exact pixels from the separate native X11 five-by-three region (15 if fully visible). These dimensions are measured from real NeXium X11 capture, not taken verbatim from the six-pixel-wide source renderer.
- No false dark attack cooldown bars in the ready image; after actual melee, no lingering READY ! pixel and **60–72** real dim cooldown pip pixels.

The X11 alert frame must precede the real strike and death captures, all must have original PNG companions and genuine independent raw P6. Each capture SHA256 is included in the new PASS report. Ten adversarial tests reject source-forged HP/cooldown/detection/input, missing stem/dot, incorrect cooldown overlap, lingering icon after strike, forged on-screen guard sprite, missing cooldown pips, and invalid image dimensions.

The exact-head NeXium emulator end-to-end test must pass again, including the previous native guard and `LOW HP` lifecycle stages and sentry hit flash, before this stage can become Ready. Native core and graphical game logic are **not edited**. This is a ROM-free authored prototype; neither commercial NES original fidelity nor physical Nintendo Switch execution is claimed.
