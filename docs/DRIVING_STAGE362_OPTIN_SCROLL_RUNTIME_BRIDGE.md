# Stage362 — source-safe finite scroll review bridge, opt-in only

## Goal and scientific limits

Stage362 adds an **optional C++17 host/libnx-compatible scene-view annotation path** for the existing finite scroll-displacement numerical observations at NES source pair starts **519–559**. It **does not** implement the NES game's camera, invent physics, replace road displacement in the active Nintendo Switch HD scene, or capture new original ROM/FM2/media. Original NES pixel art, indexed palette planes, raw CPU/PPU event rows and owner-private SHA values are neither embedded nor loaded in the source code or tests.

The observed numerical envelope is exactly the retrospective Stage361 result derived from independently verified earlier Stage359/Stage360 original captures:

| Observed original pair starts | Finite source image displacement | Number of pairs |
| --- | ---: | ---: |
| 519–526 | +3 RGB pixels | 8 |
| 527–558 | +4 RGB pixels | 32 |
| 559 only | +5 RGB pixels | 1 |
| **Total** | **157 pixels across 41 qualified consecutive observed pair changes** | **41** |

The observed switches at pair starts 527 (first 527→528 +4) and 559 (559→560 +5) are **not** predictive camera acceleration rules. They are observational evidence at exactly these original source frames. No other pair or level is supported.

## C++ integration and render isolation

Public files:
- `graphics_core/driving_source_scroll_review.hpp`: header-only `SourceScrollReviewGate`, fixed 519–559 envelope lookup, clearly typed original-source witness, `SourceScrollReviewStatus` failure outcomes and unambiguous separate `SourceScrollReviewResult`.
- `graphics_core/driving_scene_bridge.hpp`: `makeDrivingSceneSourceScrollReview(drive, gate, manual_opt_in, witness)` connects **the existing** `makeDrivingSceneView` C++ scene mapping to the optional source-review gate. This is available to a caller but is **not wired to a default gamepad gesture or enabled in the shipping libnx NRO** at this stage.
- `graphics_core/driving_preview.hpp`: adds a tiny opt-in numerical marker in the **road portion** of the ROM-free placeholder renderer. The panel uses synthetic pixels/colors/position only, and never draws original game art or overwrites the health/timer/speed HUD.
- `tests/test_driving_source_scroll_review.cpp`: **synthetic-only complete C++ host test** for real generated RGBA framebuffer effects, disabled-mode parity, source/guest event order, confidence tiers, absent first `$2005` write, missing PPU line-zero, source provenance, disagreement, flat/inconclusive frames, exact 41-pair model, guest frame skips/repeats, and no modified `DrivingState` or `road_phase`.
- `graphics_core/CMakeLists.txt`: new `romfree_stage362_optin_source_scroll_review` target, compiled with `-Wall -Wextra -Wpedantic -Werror` in GCC/Clang. All tests are ROM-free.

**Default-off:** with `manual_opt_in=false`, the gate resets, the overlay disappears, the original scene view is unchanged and game session physics remains authoritative. Creating the gate alone has no effects.

**Finite state:** the first accepted source witness must be source pair start 519. The next accepted source witness and **the guest frame number must each advance by exactly one**. A missing, repeated, reversed, wrapped or out-of-range original/guest frame fails closed and resets the gate. Review always restarts explicitly from 519; no interpolation.

**No invented evidence:** independent `source_verified`, `first_cpu_2005_y_verified`, `native_ppu_line0_verified` and `discriminating_rgb` booleans must all be true; these flags are assertions supplied by the caller, **not cryptographic or per-pixel verification** by the adapter. The caller must authenticate private original evidence separately before making a scientific source claim. Pixel-shift must match the finite envelope and **negative signed first `$2005` vertical modulo-240 step**, otherwise reject. Boundary pairs 519, 544 and 559 require `StrictFour`. Archived original intervals 520–543 and 545–558 require `ArchivedQualifiedUnknown`, because only aggregate 4/4-vs-3/4 counts are published; silently upgrading such rows to 3/4 or 4/4 is rejected. Inconclusive, mask conflict, absent original Y, unverified source, identical/flat image each rejects.

**Review result is a distinct diagnostic view.** `DrivingPreviewView::road_phase` remains the independent **invented prototype stripe displacement** sourced from `DrivingState` and is *never* derived from, added to, or replaced by the observed NES scroll. `DrivingPreviewView::speed`, `car_x`, obstacle coordinates, health and HUD are also never altered by the review. No live original NES witness/HD guest physical causation is proven by the synthetic tests.

## Verification contract and preservation of failed evidence

The host test must prove: the same guest frame drawn without review has unchanged HUD pixels, review changes only a bounded road-region panel, default-off path does not alter any screen fields, 41 accepted fabricated witnesses show 157 cumulative numerical displacement, and fabricated invalid sources fail closed. Neither the adapter nor the test code loads owner-private original game data. Host test output marker identifies synthetic-only source as `real_original_game_pixels=0`.

All original scientific results stay unchanged: Stage355's full-scene motion test **FAILED/INCONCLUSIVE**, Stage357's five inconclusive image pairs remain inconclusive, Stage359's finite +4 and Stage360's three cross-archive joins stay as observed. Stage361 remains a retrospective finite classification, not a new original holdout.

## Archive / CI

`main` remains untouched and Draft PR #99 stays Draft. Commit only ROM-free source, synthetic tests, safe numerical protocol and diagnostics to public GitHub. Archive Stage362 derived numerical synthetic CI receipts and handoff owner-private under `Project Evidence Archive — Private/Vice Project Doom HD Remake`, upload with SHA256+zip manifest and independently re-download all six primary artifacts and receipt. Never upload original ROM, FM2, original RGB frames, raw CPU/PPU rows, original palette files or private original hashes to public GitHub/CI. Mark exact-head Native Core CI, deterministic simulation and Nintendo Switch graphical scene as successful **only after checking each exact head workflow**.

Next proposed stage 363: independent original holdout beyond the previous observation window, with preregistered collection and first-Y/ROI tests, and optional separate manual NRO review control only with authenticated owner-private evidence. Stage362 is not authorization to treat an invented guest `road_phase` as NES camera speed.
