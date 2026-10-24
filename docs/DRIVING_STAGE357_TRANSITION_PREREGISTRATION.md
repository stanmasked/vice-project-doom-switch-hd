# Stage 357 — prospective original transition window 405–419

**Frozen BEFORE acquiring or inspecting any RGB frames 405–419.** This is a new, previously uncaptured contiguous source segment immediately after the all-single-color Stage355 images 380–404. It has **15 frames and 14 transitions**, not 25/24. Do not retrospectively change either segment or scoring criteria after seeing the new data.

## Original and provenance contract

Read-only replay of the exact owner-private NTSC Vice: Project Doom NES ROM and canonical taotao FM2, via FCEUX v2.6.5 classic PPU NewPPU=0, with 261-frame Stage335 CPU and Stage341 native PPU event streams frame 380–640. Save native 256x240 XBuf RGB frames **405–419**, 3 complete indexed-palette planes **405, 412, 419**, 6 RGB/index probes per frame (90), independent source manifest with 22 entries (15 GD, 3 palettes, CPU, PPU, COMPLETE, probes). Require the full CPU/native PPU prior-hash seals, FM2 readonly marker and SHA-256 for every member. Store all original/source data strictly owner-only.

## Frozen classification; do not force apparent movement

For each of 15 full original RGB frames, test whether all 61,440 pixels have the same RGB triple; count distinct frames and all 14 pairwise byte equality results. Count exact **non-flat-frame transitions** separately from uniform-to-uniform boundaries. Preserve four confidence tiers on the *same four half-open original environment bands* [(0,52,20,98),(0,52,98,175),(195,255,20,98),(195,255,98,175)] with 49 candidate signed vertical offsets [-24,+24], maximum RGB best mismatch fraction 0.16, minimum runner-gap 0.045:
1. strict all four confident, agree;
2. exactly three confident agree, fourth weak;
3. two or more confident and conflicting (must report as negative);
4. all else inconclusive.
Importantly, **every original pair with either complete image flat, both images identical, or unsupported source register anchors is counted separately**, not a validated nonzero shift or physical stationary camera. The four-mask image displacement may be qualified only from image scores. Source register Y comparison is performed afterwards on pairs with two independently verified first second-phase CPU $2005 Y anchors. If either missing, label *register unsupported*, never impute retained state.

For each original CPU/native-PPU frame count presence/absence of second-phase CPU $2005 event, and classic PPU native line-zero rendering mask==0; label four combinations separately. Read-only line-zero classic temporary PPU Y may be observed as a **distinct witness** on frames with missing CPU writes, but do not infer it equals persistent prior CPU-scrolled Y, do not treat blank rendering as camera motion, and do not claim hardware PPU dot precision.

## Negative controls and reporting

All 15 original source RGB images, 90 probes and 3 palette planes require authenticated hashes and source crosschecks. Score and report all 14 pairs including null shifts and confidence conflicts. A full scene-transition test **passes source integrity** only if authentic 15 frames, CPU/PPU seals and palettes/probes match. Whether distinct texture or scroll hypothesis passes is **empirical and may be fully inconclusive**. Keep Stage355 failure and Stage356 posthoc co-occurrence unchanged. Separately record complete original source integrity, texture-onset evidence, four-mask image tiers, available register comparisons, source mismatch counts and unsupported cases. Original ROM/FM2, raw source raster, palette index, trace rows, capture Lua and private digests must never enter public GitHub or public Actions; only code/synthetic test and source-safe numeric report.

Owner-private archive Google Drive: Project Evidence Archive — Private/Vice Project Doom HD Remake. Readback-download verify SHA-256 each uploaded item plus ZIP CRC and 22 per-source original-member hashes.

**No original Stage357 result is known or asserted when this preregistration is committed.**
