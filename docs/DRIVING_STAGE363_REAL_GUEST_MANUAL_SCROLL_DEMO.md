# Stage363 — manual ROM-free scroll-number DEMO in Nintendo Switch NRO

## Purpose and boundaries

Stage363 wires an **actual libnx gamepad chord** and ROM-free guest framebuffer demonstration into the existing manual-only driving preview of the Switch graphical NRO. This is **not** a new original NES FCEUX capture, not playback of an authenticated per-frame source witness, and **not** an implementation of source car physics, acceleration or a global NES camera. The original Stage362 `SourceScrollReviewGate` remains independent and is **not supplied with fabricated `source_verified` values**.

The authentic source basis is the previously published Stage361 finite **aggregate-only** numerical description from authenticated original source archives at earlier stages. No original ROM, FM2 recording, native NES RGB/index art, full original CPU/PPU trace or source-private SHA is embedded, loaded, published or copied to public CI.

## Real NRO manual control

1. Enter **manual** control mode (existing left-stick click or R+A).
2. Enter the existing ROM-free synthetic driving preview using **ZL + ZR + X**.
3. Within manual driving, press a *fresh edge* of **L while holding ZL + ZR**, **without R**. This starts the source-safe numerical DEMO; the same chord again stops it. Holding L does not start new sessions.
4. The manually enabled demonstration renders exactly **41 successive guest frames**, or fewer if manually switched off or if a host/guest frame discontinuity occurs:
   - 8 pairs, original numerical pair starts **519–526**, show **+3**;
   - 32 pairs, original numerical pair starts **527–558**, show **+4**;
   - 1 pair, start **559**, shows **+5**;
   - the display is turned OFF automatically after that last pair, without predicting start 560.
5. The road-only diagnostic panel explicitly says **DEMO**, in cyan against a separately invented dark teal background. It shows the published original pair start and observed displacement **only as numbers**. It does **not** claim newly authenticated source or translate source numerical displacement to physics `road_phase`.

The new chord is reserved exclusively in the manual driving scene and deliberately suppresses L's normal backdrop reload. Other camera controls, existing profile- and 37-frame road reviewers, the platformer, health HUD, vehicle collision, route exit, original synthetic traffic and game-input stepping must remain unaffected. The demo's independent controller resets on exit to platform, manual mode change, vehicle restart, preview off, or user opt-out. After an invalid, repeated, skipped or backward guest presentation frame, it resets rather than interpolating.

## Implementation

- `graphics_core/driving_source_scroll_demo.hpp` implements a **separate** `SourceScrollManualDemo`, which reads only the safe finite function `stage362FiniteShift`. It never calls original-source `SourceScrollReviewGate::observe`, never creates a `SourceScrollPairWitness` claiming `source_verified`, and never mutates `DrivingState` or `game_core`.
- `graphics_core/driving_preview.hpp` adds `source_scroll_review_demo` to the view, with explicit bitmap letters D-E-M-O and distinctive ROM-free road-only colors. Regular Stage362 source review retains its previous badge color and semantics.
- `switch_graphical/source/main.cpp` owns the manual mode and receives genuine `HidNpadButton_L` fresh edges plus ZL/ZR, includes the DEMO view on the **same real libnx drawScene** path, and suppresses the conflicting standalone backdrop reload chord. No synthetic input injection is counted as real controller proof.
- `graphics_core/driving_source_scroll_demo_guest.hpp` samples **actual framebuffer pixels** at the distinctive panel, border and DEMO first glyph after presentation. The optional owner-console SD report `sdmc:/switch/vice_project_doom/scroll_demo_guest.txt` writes bounded `on` and `last` records only when the live pixel checks pass. Every record explicitly declares `actual_original_rom_source_verification=0`, `original_game_physics_proven=0`, and `raw_rom_fm2_present=0`. Real guest NeXium control proof requires a test that supplies real controller events and recovers this file; code/test builds alone **do not prove a NeXium manual chord occurred**.
- `tests/test_driving_source_scroll_demo.cpp` tests 41 synthetic sequential raster frames, 157 cumulative finite numeric pixels, exact DEMO glyph/panel, source-safe guest witness inspection, unchanged HUD/vehicle controls/road phase, manually turning off and on, missing and duplicate guest ticks, no out-of-bounds replay, and absent DEMO marker under default `drawScene`.
- `graphics_core/CMakeLists.txt` adds `romfree_stage363_manual_numeric_scroll_demo` to native host CTest with GCC/Clang `-Wall -Wextra -Wpedantic -Werror`.

## CI and evidence rules

A successful Nintendo Switch graphical workflow supports **NRO compilation**, not necessarily NeXium guest-controller execution. The separate Native Core CI confirms host raster and C++ tests, not actual console button input. Only a separately checked NeXium run containing the new `VPD_STAGE363_NUMERIC_DEMO_V1` guest file with two witnessed `on` and `last` events may be called NeXium manual runtime proof. The exact workflow revision must match tested code.

Stage355's earlier original image-motion **FAILED/INCONCLUSIVE** result and Stage357's five inconclusive RGB-pairs remain negative/unknown as before. No original-source evidence from a new ROM/FM2 capture is claimed.

Archive all derived numerical controller contract, test receipts and handoff privately in `Project Evidence Archive — Private/Vice Project Doom HD Remake`, excluding proprietary game media. Verify SHA256, ZIP CRC and internal member SHA after independent Drive re-download. Keep [Draft PR #99](https://github.com/stanmasked/vice-project-doom-switch-hd/pull/99) Draft and `main` untouched.
