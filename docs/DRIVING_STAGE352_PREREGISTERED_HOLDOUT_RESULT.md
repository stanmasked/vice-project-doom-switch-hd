# Stage 352 — prespecified environment-only holdout result (frames 585–609)

## Source and research registration

The research protocol and ROM-free scoring code were committed on GitHub **before this particular original-frame capture**. The frozen protocol is `docs/DRIVING_STAGE352_PRE_REGISTERED_HOLDOUT.md`, commit `befda5b16eaebd20a7ecfcf11f9d1db374163314`. It freezes the four environment-only masks, their original 256×240 pixel rectangles, a -24..+24 candidate shift range, best-pixel mismatch <=0.16, runner-up difference >=0.045, and the fresh previously uncaptured frames **585–609**. The mask coordinates and thresholds were not changed after inspecting the new images.

The owner-private read-only FCEUX 2.6.5 classic PPU (NewPPU 0) ran the canonical original NTSC Vice: Project Doom ROM/FM2 and captured **25 authentic adjacent native RGB images** (frame numbers 585–609) in a newly allocated private directory. Prior owner-sealed Stage335 CPU and Stage341 classic PPU full-event files and FM2 completion marker were independently matched by SHA-256. All 32 original source files were authenticated; three full indexed palette planes and **150 independent RGB/palette point probes** were checked. Proprietary files and all original hashes stay owner-private.

## Unedited preregistered outcome

The freeze was intended as a genuine out-of-sample test of the four environment subwindows that were selected **posthoc in Stage351**. The new 24-pair results are:

| Confidence category | Pairs | Agreement with first $2005 Y modulo-240 |
| --- | ---: | ---: |
| All four prespecified environment masks uniquely agree | **19** | **19/19** |
| At least one mask fails its fixed confidence gate, or independent masks disagree | **5** | **Not asserted** |
| Qualified image/register contradictions | **0** | No contradictions among qualified pairs |

Qualified observed image displacements: **7 stationary, 1 at +1, 1 at +2, 1 at +4, 9 at +5 pixels**. These sum to 19. Five other original transitions remain **inconclusive**, not mismatches and not verified matches.

This is the correct strict interpretation: **19/24 source pairs qualified and all 19 matched the finite modulo-240 hypothesis; five were inconclusive under locked criteria.** The fresh holdout is stronger evidence than the posthoc Stage351 rescue, yet it neither supplies 24/24 coverage nor supports a global game-scroll/camera/vehicle-speed law. No changes to motion thresholds or masks were made after the capture; the five failures are preserved for new studies.

## Owner-private permanent source archive

- [Stage352 owner-private original RGB+CPU+PPU ZIP](https://drive.google.com/file/d/1hwSwNKFxrwSEZUQdqHoJ90u2YlIuddJ_/view): 2,159,623 bytes, 37 members, containing 32 original per-file SHA-pinned source members and five restricted service files. ROM and FM2 excluded.
- [Owner-private Stage352 source manifest](https://drive.google.com/file/d/1qi-vDux2waEfebyOTlddSPqkfdZmdSsr/view).
- [Private aggregate](https://drive.google.com/file/d/1eZSTFuoVAO4D1FIJrfAgfetQog2cjja4/view).
- [Private per-pair confidence diagnostic](https://drive.google.com/file/d/1c2yVWwMv_exPWfcf6J2sSNRuxMfh_dRc/view).
- [Private preupload source seal](https://drive.google.com/file/d/1B6ietV1yQLk-NRlhkWgibXapMTFPzZc5/view).

All five were uploaded to owner-only Project Evidence Archive folders, then fetched back from Google Drive as fresh bytes and matched to the local preupload SHA-256. The restored ZIP passes CRC and all 32 member SHA-256 comparisons. A separate private readback-verification receipt records exact checked files and proof of permanence.

## Public ROM-free code, CI and limits

- `tools/audit_private_stage352_preregistered_holdout.py` stores the immutable four mask rectangles and fixed thresholds and independently SHA-checks owner-private original witnesses. Its result format differentiates qualified matches, genuine contradictions, unsupported PPU values and inconclusive pixels.
- `tests/test_stage352_preregistered_holdout.py` supplies **12 manufactured-only checks**, with explicit contradiction retention, correct treatment of flat/ambiguous textures, frozen coordinates and rejection of missing frames.
- `docs/stage352_public_aggregate.json` contains only safe aggregate counters without original images, register bytes, private hashes, ROM or movie.

[Native Core CI #40042571763](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/40042571763) completed **SUCCESS** on the protocol-locked `befda5b1` revision. Adding the subsequent evidence report and public aggregate constitutes a new branch revision requiring a fresh exact-head check; do not rely only on the protocol CI for later commits.

The candidate association here remains the **software register/image relation** for this frame window. No specific NES physical PPU dot, automatic road rasterization, general camera velocity, automobile handling or collision is proven. Keep PR #99 Draft; main stays unchanged.

## Next research step

A Stage353 extension should **pre-register an independent strategy for the five inconclusive scenes** before testing a new unseen capture. Suggested approach: fixed non-overlapping larger environment regions or an optical-flow estimator with calibrated negative synthetic controls, while retaining the Stage352 masks unchanged as an original baseline. Hold new original source/derived artifacts privately under the same SHA-verified Drive archive protocol.
