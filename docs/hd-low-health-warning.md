# Stage 83 — source-driven HD low-health visual cue

The independent real NeXium test in **PR #61** proved that first sentry impact reduces HP from 5 to 4, flashes the hero for 16 native simulation ticks, returns to a normal-looking hero, and leaves precisely one lost heart.

This stage adds one **optional user-facing visual treatment**, not another damage rule: at **one or two remaining health points**, a tiny `LOW HP` text and a red underline appear adjacent to the existing HERO heart HUD, pulsing **12 simulation frames on and 12 off**.

## Safeguards

- It is activated only in manual play by the same existing L+R HD visual setting. It is invisible in the original ROM-free autoplay demo and when the user has turned HD effects off.
- It is suppressed for HP **0** (where the defeat overlay already applies), HP **3–5**, and on the cleared stage.
- The five HP segments (x=761..831, y=18..29) **are never modified**: the indicator is drawn below and alongside the existing slots (red line x=757..835, y=34..36; `LOW HP` label x=846..~915, y=17..30). This intentionally preserves prior exact native X11 five-heart audits.
- Driven by authoritative `SceneView.player_health` and `SceneView.frame` values coming from the shared `Simulation`/render bridge. It does not advance a private timer, restore HP, alter collision or input, affect projectiles, or change the framebuffer outside the HUD warning region.
- Existing HD ON/OFF native same-frame alternate rendering now toggles the new layer as part of the same HD effects preference.

## Regression coverage

A new strict host C++ test `tests/test_hd_low_health_warning.cpp` performs an actual guarded encounter with repeated source `Right` until **three real melee strikes** reduce hero health from 5 to 2. Then it verifies:
- The real simulation-to-scene bridge presents HP2 and displays the warning with HD on, absent with HD off.
- Full RGBA frames are bit-identical **outside the two warning rectangles**, especially inside each of the five source-owned heart slots.
- The 12-on/12-off warning phase is determined purely by simulation-frame parity.
- At HP0, HP3, HP5, stage clear, or any autoplay frame, enabling the warning changes **zero pixels**.
- The complete source-gameplay fingerprint remains unchanged by any of the rendering tests.

CI includes the new CTest in graphics host builds, a complete Switch NRO build, Native Core / Debug / Release tests and NeXium regression workflow. **This source change is not yet verified by CI or genuine NeXium**. It is an original clean-room cosmetic cue only; no commercial ROM/assets were added, and no claim of NES-original or physical Switch fidelity is made.
