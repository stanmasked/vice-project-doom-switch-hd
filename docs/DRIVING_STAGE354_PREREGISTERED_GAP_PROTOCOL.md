# Stage354 — preregistered unseen gap-window RGB/PPU test

**Protocol frozen before any capture or inspection of previously unsampled original frames 495–519.** The ROM-free source and 17 manufactured-only tests were committed at cb5e1807df4c9fe23db6569679dd782dadab8ae2 and b28055124bf728794611afc0ca98b03bd4b675c8. This source window sits between independently archived captures 470–494 and 520–544 and cannot be retroactively exchanged for another interval if results are unfavorable.

## Fixed owner-private original source and program

FCEUX 2.6.5 classic PPU (NewPPU 0), read-only NTSC original ROM and taotao FM2. Collect 25 native 256×240 XBuf RGB images for frames 495–519, 24 adjacent pairs, indexed palettes at frames 495,507,519, and independently sealed complete 261-frame CPU Stage335 / native PPU Stage341 traces. Original ROM, movie, raster, raw register events and all private source digests remain owner-only.

## Confidence masks and hypotheses — unchanged from Stage353

Exact half-open source RGB rectangles:

| Mask | Coordinates (x0,x1,y0,y1) |
| --- | --- |
| left_env_upper | (0,52,20,98) |
| left_env_lower | (0,52,98,175) |
| right_env_upper | (195,255,20,98) |
| right_env_lower | (195,255,98,175) |

Every region independently scans **49 signed offsets −24..+24**. A band is confident if its RGB best mismatch <=0.16 and its runner-up gap >=0.045.

- Strict 4/4: four confident regions agree.
- Preregistered 3/4: precisely three confident regions agree, fourth fails confidence.
- **Explicit mask conflict:** any two confident regions select differing shifts, including three against one; do not filter this out.
- Inconclusive: at most two confident regions, no confident disagreement.

Determine the source pixel shift from RGB **without using** the independently captured PPU scroll to choose it; only afterwards compare qualified shifts with the inverse minimal signed conventional modulo-240 first second-phase $2005 Y delta. Count register contradictions and unsupported Y 240–255 or half-period steps distinctly from mask conflicts/inconclusive results. Do not tune masks or thresholds after capture to increase success. Report a failed holdout as failed or inconclusive as observed, not as a hidden exclusion.

## Privacy and source authentication

Require a separately pinned new 32-file manifest SHA-256, original read-only completion/ROM identity, independently pinned previous Stage335/341 full CPU/native PPU trace hashes, 261-frame event anchors, 25 native RGB/GD files, three indexed palette planes and 150 RGB/palette point probes. ZIP CRC and all 32 original file SHA checks plus owner-private Google Drive upload/download SHA readback are mandatory. Public CI runs source-free synthetic fixtures only. No changes to actual car physics, geometry, collision or generalized camera speed can be inferred from a bounded texture experiment.

**This preregistration contains no Stage354 original results.**
