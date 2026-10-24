# Stage375 — fresh original FCEUX RGB/CPU/native-PPU holdout (656–670)

**Status: frozen before ANY owner-private 656–670 original RGB exposure.** 2026-10-24.

## The previous result remains unchanged

Stage374's preregistered first evaluation of 641–655 is **14 image-inconclusive of 14**, zero image-qualified register comparisons. Its narrow road-marking strips have low score separation under the predeclared 0.045 runner-up gap, while two environment parent rectangles discriminated. A later *posthoc* parent-environment-only view (+2 x1, +5 x12, +8 x1) is **exploratory training data only**, not a retrospective 14/14 Stage374 pass. Earlier Stage355 and Stage357 negative/inconclusive observations remain unchanged.

## Prospective independent source window

Read-only canonical original Vice: Project Doom NTSC ROM + canonical taotao FM2, verified independently by full SHA-256 in owner-private storage; instrumented FCEUX v2.6.5 with **classic PPU NewPPU=0**. No source assets, images, original source hashes, CPU/native trace rows or private capture Lua in public GitHub/CI.

The *untouched* target is original frames **656–670 inclusive**, exactly **15** native 256×240 XBuf RGB GD images and **14** adjacent original image pairs. Three complete palette-index planes at frames **656, 663, 670**; six independently corroborated pixel/color/index points per RGB frame (90). Same-session authenticated native classic-PPU frame-zero scanline and CPU second-phase `$2005` Y anchors for all 15 frames. Fresh capture covers original CPU/native frames **380–670 inclusive = 291** (rather than the earlier 276); compare its byte prefix 380–655 to previously independently sealed Stage374, not full different-length hashes.

**Selection novelty gate:** The prior frame RGB archives inspected at protocol design end at <=655 (other available captures cover earlier ranges). If a prior 656–670 original RGB capture is discovered before execution or later, note this explicitly and do not claim independent fresh holdout. There is no requirement that the next 15 frames visibly contain a moving road: stationary/transition material can legitimately yield an inconclusive test.

## PRECOMMITTED four ROI masks, unchanged from Stage352/359

All rectangles use half-open `(x0,x1,y0,y1)` coordinates and are not edited after seeing images:

- `left_env_upper=(0,52,20,98)`
- `left_env_lower=(0,52,98,175)`
- `right_env_upper=(195,255,20,98)`
- `right_env_lower=(195,255,98,175)`

Score each of four independent environment regions over **integer signed vertical offsets −24..+24**, with exact RGB per-pixel mismatch at the best shift `<=0.16` and runner-up minus best `>=0.045`; reject flat texture and nondiscriminating aliases. Return 4/4 strict, guarded 3/4 (the fourth must NOT confidently contradict), mask conflict, flat, or inconclusive. Missing original image and index probes, out-of-order source frame, substitute inputs, wrong source SHA or unexpected emulator mode make source authentication fail. Do not tune the masks, offsets or thresholds after seeing frame RGB; do not use PPU to choose the shift.

Only independently qualified image shifts are compared to the observed opposite signed modulo-240 delta of **first second-phase `$2005` Y**, with source CPU/native line-zero order and ownership verified for each frame. Missing first Y, unsupported values 240–255, ambiguous 120 or contradictory native source anchors => unsupported or reject, never inferred image agreement. Report all 14 frame-pair categories and register matches, contradictions, unsupported cases, and unqualified pairs individually and in aggregate. No silence on failures.

## Methods, testing, storage and inference limit

The pure numeric `tools/stage375_environment_motion_contract.py` and fabricated-only `tests/test_stage375_environment_motion_contract.py` are committed with this protocol **before** live capture (23 regression cases cover masks, thresholds, flat/alias/conflict, source absent, modulo wrapping and no promotion). These ROM-free tests do not prove authentic original gameplay or establish source identity. Preregistration exists to prevent post-hoc tuning, not to guarantee success.

The owner-private capture must be written to a new mode-0700 directory outside Git, with immutable pre-execution binary/ROM/FM2/private-Lua SHA pins. Record exact source provenance and 291-frame complete markers, construct SHA-256/size manifest for all private members before analysis, and perform a separate independent audit. Original NES ROM/FM2 stay in the canonical private originals area, **not inside derivative evidence ZIPs**. Archive both successes and failures privately in Google Drive and independently redownload for full SHA-256, ZIP CRC and file-member checks. Public artifacts may contain only source-free code, synthetic fixtures and nonrevealing aggregate statistics after verification.

Even a genuinely independent strong image vs register match would be evidence only about this finite 14-pair window. It would **not** validate generalized NES camera physics, car speed, collisions, perspective geometry or hardware PPU-dot timing.

**Results must be written in a separate document, preserving this frozen preregistration and reporting inconclusive/contradictory results as such.**
