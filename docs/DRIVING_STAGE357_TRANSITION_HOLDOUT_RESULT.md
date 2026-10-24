# Stage357 — authentic original 405–419 transition holdout result

## Experiment was preregistered before FCEUX capture

GitHub commit `cc321ed233f3e864ff1d5ade3ce49bb2ea284bf1` froze the previously not captured native 405–419 image interval, **15 original frames and 14 adjacent pairs**, all four half-open RGB environment coordinates from Stage353, 49 candidate signed shifts from -24 to +24, confidence thresholds max best mismatch 0.16 and minimum runner gap 0.045. This is a new holdout relative to original source Stage355's 380–404 uniformly colored frames. Stage355's failed/inconclusive fixed-ROI gate and Stage356's posthoc diagnostic remain unchanged.

After preregistration, the owner-private authentic NTSC ROM and taotao FM2 were replayed in FCEUX 2.6.5 classic PPU (NewPPU=0). Captured all 15 consecutive authentic native 256×240 RGB images, 3 full original index/palette planes at 405/412/419, and verified 90 original RGB/palette probes. Original complete 261-frame CPU Stage335 and native classic PPU Stage341 trace SHA-256 values, ROM identity/read-only FM2 marker, and all 22 original source-member SHA-256 checks reproduced independent prior-source seals. No original game data or owner-private hashes were placed in this public result.

## Source observations under frozen RGB confidence tiers

| Original source observation | Count |
| --- | ---: |
| Authenticated original native RGB frames | **15** |
| Frames consisting of one single RGB color | **4** |
| Distinct complete original RGB frames | **12** |
| Adjacent full-RGB byte-identical image pairs | **3/14** |
| Original image pairs with ≥1 flat frame | **4/14** |
| **Strict four-of-four** qualifying environment shifts | **9/14** |
| Three-of-four only confident source image shifts | 0 |
| Confident image-mask conflicts | 0 |
| Inconclusive image pairs | **5/14** |
| Missing required first second-phase CPU PPU $2005 Y anchors | **0/15 frames** |
| Native line-zero classic PPU mask=0 | **0/15 frames** |
| Qualified image shifts matching inverse first second-phase $2005 Y modulo-240 | **9/9** |
| Qualified image/register contradictions | 0 |
| Qualified original image shifts lacking independently validated scroll anchor | 0 |

A real image-texture transition occurs within this original 405–419 sequence: the prior 380–404 window had 25 identical one-color images, while this new capture has eleven non-flat frames, 12 distinct complete native images and 9 uniquely qualified cross-region displacements. All 9 qualified source-image displacements agree with their independently validated native PPU scroll-register source witnesses. The remaining **five stay inconclusive**; do not promote uniform/identical images into motion evidence or impute alternative register values. No physical car speed, road perspective, collision, universal camera behavior or hardware PPU dot timing was established.

## Permanent owner-only source archive and independently verified recovery

- [Original source RGB CPU/PPU archive](https://drive.google.com/file/d/1eBaQ0drBK0hCyQvzc5eMSa37fclx02ad/view) — 2,091,601 bytes, 27 ZIP members (22 SHA-pinned original source members plus 5 service files; **ROM/FM2 excluded**).
- [Original 22-member private source manifest](https://drive.google.com/file/d/1iqlfhr_0tsisyvooBX3KmBGY5L32dehU/view).
- [Private owner-local aggregate](https://drive.google.com/file/d/1uIsrqpGnOKxF7tIMdUmnO8cRNRWnzZvB/view).
- [Private per-pair and per-frame diagnostics](https://drive.google.com/file/d/1cWm-sNPa7T92Ul2PslMTaJi3OyQ2aROB/view).
- [Private preupload SHA/ZIP seal](https://drive.google.com/file/d/1mIn0M7Q-NJ89Q_pB5saBn6oCxUTt4N-0/view).
- [Private independent Drive postupload SHA/ZIP recovery receipt](https://drive.google.com/file/d/1kFcHRoQHEpdP2ezXeeuCRbzELjcXtdBe/view).
- [Stage357 private handoff](https://drive.google.com/file/d/1u-srMHQTATdOFZwZk19DUkBtYUW9MXxN/view).

All six original archive/manifests/results/handoff objects independently downloaded from owner-only Drive, verified byte-for-byte SHA-256 and exact file size. ZIP CRC passed; **22/22** original per-member SHA-256 checks repeated on the *downloaded archive*. Copyrighted original ROM/FM2 bytes excluded. No game images, private CPU/PPU trace rows or private source hashes in public repository.

## Code/CI and next check

- `tools/audit_private_stage357_transition.py` — source-authenticated fail-closed 15-frame audit and independently measured image-confidence tiers.
- `tests/test_stage357_transition.py` — 17 fabricated-only unit regressions for 15-frame coverage, four-mask agreement, ambiguous frames, scroll-anchor omissions and contradictions.
- `docs/DRIVING_STAGE357_TRANSITION_PREREGISTRATION.md` — immutable prior-source protocol.
- `docs/stage357_public_aggregate.json` — sanitized original numerical results without original data.

Native Core CI and Deterministic native simulation succeeded on the protocol+test commit `2d5ed3a47023be9797752e6c3abcd8518765c0a7`. Exact postcapture report-head CI must also be checked and must not be assumed successful. Keep Draft PR #99 open and main unchanged. Stage358 can investigate detailed visual transition timing as **exploratory** work but must not reinterpret Stage357's 5 original inconclusive pairs or Stage355's failed gate.
