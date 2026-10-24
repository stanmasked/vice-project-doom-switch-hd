# Stage353 preregistration — independent 3-of-4 RGB holdout

**Frozen before any original frames 610–634 are captured or inspected.** The scoring source and 17 entirely fabricated tests were first committed at d5be01428bc76c322d8d3a118d79a7482e8ccb9c and 7535241ecbc20396f6513710366cde96eae0b20f. The source window, confidence rules, ROI geometry, and shift limits must never be changed as a reaction to the original holdout.

## Fresh replay selection

New read-only owner-local original NTSC Vice: Project Doom ROM/FM2 replay, FCEUX v2.6.5 classic PPU (NewPPU 0), **25 frames 610–634, 24 adjacent pairs**. Original 585–609 Stage352 frames were training observations and cannot serve as the fresh holdout. Native XBuf frames 256×240; palette-index planes 610,622,634.

## Fixed source RGB coordinates and confidence

Half-open rectangular image regions, identical to Stage352:

| Region | (x0,x1,y0,y1) |
| --- | --- |
| left_env_upper | (0,52,20,98) |
| left_env_lower | (0,52,98,175) |
| right_env_upper | (195,255,20,98) |
| right_env_lower | (195,255,98,175) |

For every ROI independently evaluate all **49 signed vertical offsets from -24 to +24**. A region independently qualifies if the best mismatch fraction is <=0.16 **and** the second-best minus best mismatch fraction is >=0.045. Select visual shifts strictly **before** looking at the first second-phase PPU $2005 Y value or modulo-240 prediction.

- **Strict:** all 4 confident regions agree on the same image shift.
- **Three-of-four:** exactly 3 confident regions agree, and the fourth is NOT confident.
- **Conflict:** at least 2 confident regions select different shifts, including when three agree but the fourth strongly disagrees. Explicit negative evidence, never silent exclusion.
- **Inconclusive:** at most 2 confident regions with no confident disagreement. No image displacement asserted.

After assigning the independent RGB tier, compare qualified shifts with the negative of the minimal signed modulo-240 $2005 Y delta; unsupported original values outside 0–239, contradictions, mask conflicts and ambiguities are each explicitly counted. This is not proof of vehicle speed, physical camera motion, collision, scene geometry or exact hardware PPU dots. The prior Stage352 19/24 four-region gate remains unchanged.

## Source provenance and private retention

An authentic result requires independently pinned original Stage335 CPU and Stage341 native-PPU complete-trace SHA-256, a new independently pinned exact 32-file manifest, read-only ROM/movie completion and original 261-frame trace coverage, 25 genuine GD RGB images, three indexed palette planes and 150 RGB/palette cross-probes. Fail closed on malformed inputs, missing frames and source changes. Archive all original rasters, register events, private Lua and owner-only checksums in private Google Drive; public GitHub gets only source-free code, fabricated tests, and safe numerical counts. Re-download all private evidence from Drive and compare whole-file SHA-256, ZIP CRC and 32 per-source digests.

**This document was committed before the new 610–634 capture: no original holdout results are asserted in this preregistration.**
