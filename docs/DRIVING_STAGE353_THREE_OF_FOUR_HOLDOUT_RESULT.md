# Stage 353 — original 610–634 holdout result under frozen 3-of-4 criteria

## Preregistration and source provenance

The entire source-free original-source audit, its 17 synthetic negative tests, exact RGB ROI geometry, shift range and four confidence tiers were committed in GitHub *before* running the new original FCEUX replay. Frozen source protocol: commit 1cf34a0e1e8ee4ed63ec00ade275a1e1e2eafec1, documentation DRIVING_STAGE353_THREE_OF_FOUR_PREREGISTRATION.md.

After that commit, an owner-private, read-only FCEUX v2.6.5 legacy/classic PPU replay with the original NTSC Vice: Project Doom ROM + 43,652-input taotao FM2 captured **25 consecutive native 256×240 XBuf RGB frames 610–634**. The entire source CPU Stage335 and native PPU Stage341 traces were independently SHA-256 identical to previous original-stage source seals, and the FM2 completion marker matched the previous replay. Three 256×240 palette-index planes and **150 independent original RGB/palette sample probes** matched. The resulting manifest authenticates all **32 original-source members**.

## Original holdout result — no postcapture threshold changes

The fixed image-only confidence decision (49 signed vertical shifts -24..+24, source rectangles and thresholds max mismatch 0.16/minimum runner-up gap 0.045) was applied before evaluating the independent first second-phase $2005 Y modulo-240 prediction:

| Frozen evidence tier | Original consecutive image transitions |
| --- | ---: |
| Strict consensus: four of four individually confident and agreeing image masks | **18** |
| Preregistered three-of-four: exactly three confident, agreeing; fourth not confident | **6** |
| Contradictions among confident image regions | **0** |
| At most two confident masks; no positive image displacement asserted | **0** |
| **Total qualified RGB transitions** | **24/24** |

All **24/24** independently selected source-image shifts agree with the inverse signed modulo-240 first-scroll register difference. No original-source mismatch was concealed or treated as inconclusive. Observed image shift distribution across the 24 pairs: **0px×5, +1px×1, +2px×1, +3px×1, +4px×1, +5px×15**.

This is an independent held-out window relative to Stage352, which had 19 qualified and 5 inconclusive transitions with the strict four-of-four rule. Stage353 is a validation of the **predeclared 3-of-4 confidence rule in a fresh 25-frame sample**, not evidence that all NES/PPU states or all stages of this game follow a universal simple camera model. The 6 three-of-four pairs are a different, lower confidence evidence tier than the 18 four-of-four matches. The original Stage352 result is preserved unchanged.

## Source privacy and durable evidence

The original owner-private replay archive is in [Stage353 original RGB CPU PPU ZIP](https://drive.google.com/file/d/1GExTJxJlWlbjEFPe3W1qkZiz7lEI4T_k/view), 2,154,344 bytes (37 members). It contains 32 original-source SHA-pinned members, separately sealed manifest, owner-local source-only aggregate, 24-pair private diagnostics, private capture Lua, and the owner-local FCEUX session log; it **does not contain ROM or FM2 copies**. All original game raster pixels/CPU-PPU trace rows and original-only hashes remain owner-private:

- [Owner-private 32-file source manifest](https://drive.google.com/file/d/1JZ0Vu9ytwNXxwF7Ki6Fyz3MNht2m_qVo/view).
- [Owner-private source-derived aggregate](https://drive.google.com/file/d/1vNB-Y627TQPEuTmEEyqocX-mw9xW_bYe/view).
- [Owner-private per-pair confidence diagnostics](https://drive.google.com/file/d/1bUH_Msab_Elof30UFrPDmgZLtyiuevbM/view).
- [Owner-private preupload provenance seal](https://drive.google.com/file/d/1jFaGZseSLBfMgEZTMkc-__2z0HxcQ7AZ/view).
- [Owner-private independent Drive readback verification receipt](https://drive.google.com/file/d/1jg7iH91_jJEK5Y6oy2-tjohOvrHdonPm/view).

All five original stored files were independently **downloaded back** from owner-only Drive; each downloaded SHA-256 matched its preupload local bytes and file size. ZIP CRC passed and every one of the 32 independently manifest-listed original-source members matched SHA-256. No ROM/FM2 originals were uploaded with this derived archive.

## Public code and claims boundary

- tools/audit_private_stage353_three_of_four_holdout.py: explicit source-file authentication, four preselected independent image masks, preregistered four confidence categories; returns safe aggregate counts only.
- tests/test_stage353_three_of_four_holdout.py: 17 fabricated-only tests, including four-confident mask contradictions that cannot be ignored.
- docs/stage353_public_aggregate.json: sanitized original observation counts; no raw pixels, per-pair private diagnostics, source digests, copyright files or private capture scripts.

The native core GitHub Actions CI #40043463206 passed the locked preregistration code head, before this result document was added. The final result-head CI must be checked independently. Leave PR #99 Draft and main unchanged.

### Next scientific gate

Predeclare a new original contiguous source interval (e.g., 635–640 is too short for 25-frame coverage; a broader replay must extend existing instrumentation beyond frame 640), and investigate non-scrolling scenes / raster changes or another game level. Do not infer vehicle acceleration, steering, collision, road geometry, 3D perspective, or physical PPU cycle/dot from bounded texture displacement.
