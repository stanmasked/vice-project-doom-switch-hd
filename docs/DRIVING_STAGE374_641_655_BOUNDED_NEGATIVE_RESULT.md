# Stage374 — genuine original NES 641–655 holdout, inconclusive pixel motion

Date: 2026-10-24. Research branch: `research/stage374-preregistered-original-641-655-holdout`. Parent Stage373 provenance branch and PR #101 remain Draft; `main` is untouched.

## Preregistration correction

The preliminary owner-private Stage374 suggestion of 560–574 overlapped **previously observed Stage351 560–584** and was invalid as a new holdout. A corrected prospective holdout for **641–655**, with fixed Stage344 masks and scoring limits, was committed at `3ef2dbc0b61d9de98f2647f9e18d9f1d01ba71ba` BEFORE the new original pixels were accessed. The earlier document is retained privately as an audit trail; prior Stage351 results have not been rewritten.

## Actual read-only original FCEUX replay

Owner-private canonical NTSC Vice: Project Doom ROM and FM2 were verified against prior source pins. Instrumented FCEUX 2.6.5 classic PPU captured **276 consecutive native CPU and PPU frames 380–655**, 15 native 256x240 GD RGB frames 641–655, three full original indexed palette planes and 90 independent RGB/index probes. Earlier 380–640 CPU/native trace bytes match the beginning of the extended records **exactly** against a separately archived Stage359 capture. All 15 new frames have same-session first-Y CPU/native scanline-zero anchors. Full original ROM and FM2 were read-only; they were not put in GitHub or CI.

The initial owner-private attempt was *rejected* without a COMPLETE marker: an old close-out assertion required **253 comparisons** for the previously shorter 261-frame session. A private, narrowly-scoped capture-script repair changed ONLY that fixed count to verify actual matches against actual comparisons. The second run produced COMPLETE for 276 frames, **1,070/1,070** instruction-bound $2005 writes and **268/268** comparisons with live RAM $0D. Across the two actual original replays, all 15 RGB frames and all three indexed planes matched byte-for-byte. The rejected attempt and successful rerun are separately preserved privately; the first is not valid scientific input.

## Result under FROZEN pixel-motion gate

Predeclared four Stage344 regions: left/right environment plus two road marking strips; signed candidate shifts **−24..+24**, max best exact RGB mismatch **0.16**, min runner-up gap **0.045**, allow strict 4/4 or guarded 3/4 with no conflicting confident fourth region.

| Original frame-pair category | Observed count |
| --- | ---: |
| Strict confident 4/4 shift | **0** |
| Guarded confident 3/4 shift | **0** |
| Image ambiguous/inconclusive | **14** |
| Confident mask conflict | **0** |
| Flat image pair | **0** |
| Qualified image vs CPU/native $2005 register agreement | **0** |
| Qualified image vs register contradiction | **0** |
| Pairs that cannot be scored against register | **14** |

**Scientific acceptance FAILED/INCONCLUSIVE.** There were no qualifying RGB displacement measures. Consequently, 0 contradictions does **not** mean 14 register agreements. Do not fill gaps with the Stage361 +3/+4/+5 numeric review overlay or reinterpret all 14 as observed +5. The masks, thresholds and outcomes remain unchanged after source exposure. These observations do not validate game-camera speed, driving/car physics, collisions or hardware PPU-dot timing.

A **17-case manufactured-only** negative/regression suite was run locally after the original capture; it tests strict 4/4, guarded 3/4, conflicting masks, invalid/tied/flat bands, no imputation, missing Y, modulo-240 wrap and rejection of 14/14 unsupported evidence. These tests protect later interpretation, but were **not** all committed before the first original frame capture; the order-of-operations limitation is recorded rather than erased. Real original source replay and independent per-member SHA checks occurred only owner-privately; green public CI tests would not constitute original gameplay validation.

## Preservation

All private original source-derived frames, CPU/native PPU event rows, palette indices, per-pair numerical scores and full source SHA identities are stored only in the owner's private Google Drive archive. Two ZIPs retain both the successful attempt and the rejected first attempt, excluding original ROM/FM2; full Google Drive readback matched **8/8** uploaded files by byte size and SHA-256, with CRC verified in both ZIPs and all **22/22** successful source members SHA-matching the sealed private manifest. Personal source assets are not published.

## Next investigation

Stage375 should classify **why** those prespecified ROI scores were inconclusive, explicitly as exploratory analysis on already observed training data, then preregister truly unused original frames (candidate 656–670) and source-safe tests before fresh capture. No post-hoc mask improvements may be credited as Stage374 heldout confirmation. Stage355 early-window negative and Stage357 five inconclusive pairs remain unchanged.
