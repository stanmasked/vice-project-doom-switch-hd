# Stage358 — original early-graphics onset and PPU event co-occurrence

**Evidence classification: retrospective analysis of the previously captured owner-private Stage357 original frames 405–419, NOT a new preregistered original holdout.** The Stage357 protocol, 9 independently qualified fixed-region zero-pixel scroll-image matches, 5 ambiguous transitions, and the earlier Stage355 380–404 scientific failed/inconclusive motion gate remain unmodified. Do not claim additional new test samples or fresh FCEUX playback for Stage358.

## Independent owner-private source authentication

The original 27-member Stage357 source archive was checked against its independent Stage357 manifest seal and all **22/22 original SHA-256-pinned source files** (15 original native 256×240 GD RGB frames, 3 full indexed palette planes, native CPU/PPU full 261-frame event traces, read-only FCEUX completion and source RGB/palette point probes). The complete CPU Stage335 and native classic PPU Stage341 traces were additionally compared against the older owner-only Stage355 original manifest. No original ROM/FM2 copies are in the derived Stage357 ZIP; none is included in the new derived Stage358 ZIP.

## Frame-precise new descriptive measurements

| Observed property in genuine native source frames 405–419 | Result |
| --- | ---: |
| Single-color, mutually byte-identical frames before onset | **405–408** (4 frames) |
| **First nonuniform complete native RGB frame** | **409** |
| Whole-screen RGB pixels different between frames 408 and 409 | **36,854 / 61,440** (59.98%) |
| Second whole-screen texture/graphics change | **416→417** |
| Pixels changed between frames 416 and 417 | **8,312 / 61,440** (13.53%) |
| Frames at which **all four** previously fixed source environment regions changed versus preceding frame | **409, 417** |
| All other adjacent transitions that changed any of the four environment regions | **0** |
| Classic PPU native line-zero mask nonzero | **15/15 frames** |
| Frames with additional CPU $2000, $2006 and $2002 reads | **409, 417** |

In exactly the **same frames 409 and 417** that change all four source RGB environment regions, original CPU event frequency rises from usual 2 → 4 writes to $2000, 10 → 14 writes to $2006, and 2 → 4 reads of $2002. These three count changes co-occur with broad RGB screen changes, but **no causal link is established** by this descriptive finite-sample observation. In particular, the native line-zero rendering mask is already nonzero in flat frames 405–408, so a simple mask-off to mask-on transition at frame 409 is **not supported** by this source witness.

Complete 8-bit indexed palette planes captured at 405, 412 and 419 independently contain **1, 5 and 7 distinct palette indices**, respectively. Distinct complete RGB images: 12/15 (4 identical early blanks, 11 non-flat native screens). Later full-frame changes between 311 and 402 pixels per pair in this finite interval do not constitute original background/camera shifts; their four environment bands remain unchanged except at scene-update frames. Do not call them 'car movement', sprite collision or precise PPU dot timing.

**Qualification of prior original Stage357 evidence:** all nine *strict four-region* displacement matches in Stage357 selected **zero-pixel** environment displacement, and all nine matched **zero** signed modulo-240 source first $2005 Y delta. Five original image pairs remain inconclusive, including the 408→409 texture appearance and 416→417 broad visual change. The posthoc Stage358 results cannot be reclassified into independent motion evidence.

## Public source, tests and owner-private archival discipline

- `tools/audit_private_stage358_render_onset.py`: checks privately pinned authentic Stage357 manifest/22 original source SHA digests, independently sealed original complete CPU/native PPU streams and all 261 frame anchors, 3 indexed palette planes, 90 point probes, source-native GD RGB decoding and per-frame CPU/PPU event counts. Emits only a source-free numerical summary.
- `tests/test_stage358_render_onset.py`: **18 manufactured-only regressions** for native RGB flatness, per-pixel counts, ROI boundaries, CPU event counts, zero-mask negative controls, onset, co-occurrence without causation, failed older gate invariants and source-frame completeness.
- `docs/stage358_public_aggregate.json`: safe original counts with no copyrighted pixels, raw CPU/PPU source, private hashes or ROM/FM2.

Owner-only Drive archive:
- [Derived five-member analysis ZIP, 6,294 bytes](https://drive.google.com/file/d/1LElBJlWxFrHSjgt01wUQR1XTIMlw0UY7/view) — **no** original ROM/FM2/GD RGB/full CPU/PPU data.
- [Private aggregate](https://drive.google.com/file/d/1yzlvP4_HWWJEJFE7HghMd0cpt3ARiq24/view)
- [Per-frame private numerical diagnostics](https://drive.google.com/file/d/1Q0eeqMDwLBD0Dd2BSKvH_CLkRxEGNdB4/view)
- [Five-member SHA manifest](https://drive.google.com/file/d/1KDFCSmjuPN7Sw_oLfo1GzznnSCM_c-6v/view)
- [Private preupload SHA seal](https://drive.google.com/file/d/1_5H-FT3MVp_ZBoqpOY83MuiuHg-vSRFy/view)
- [Stage358 handoff](https://drive.google.com/file/d/1_ozEZSM4t9fx7jKnjyplP8VYYnBQUG8Z/view)
- [Original immutable Stage357 source evidence](https://drive.google.com/file/d/1eBaQ0drBK0hCyQvzc5eMSa37fclx02ad/view), retained separately.

All six Stage358 private output assets were independently **downloaded back** from owner-only Drive with exact byte counts and full matching SHA-256, ZIP CRC valid, and all five derived ZIP member SHA digests verified. The separate readback receipt is retained under `00_Manifest_and_SHA256`.

## Next research

A future Stage359 **new preregistered** original interval (e.g. uncaptured 545–559, **15 frames and 14 pairs**) can test changes beyond the early-graphics onset and contrast nonzero texture movement, before any new authentic RGB capture. Freeze the source window, scoring assumptions and 3 of 4 versus 4 of 4 confidence rules before replay; no retroactive changes to Stage355, Stage357 or Stage358. Keep Draft PR #99; main unchanged.
