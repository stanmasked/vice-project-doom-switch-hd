# Stage360 — original four-archive boundary continuity result

**Scientific status:** retrospective independent SHA-reauthenticated comparison of EXISTING original-source captures; not new original FCEUX replay nor a fresh held-out sample. Frozen Stage360 cross-archive protocol `docs/DRIVING_STAGE360_CROSS_ARCHIVE_PROTOCOL.md` committed first as `b8d3f41d38b31864ca747d856801de01edf7a6ed`. The four original RGB windows were already observed individually at Stage354, Stage350, Stage359 and Stage351.

## Audited source evidence

Four independently pinned owner-private original FCEUX Classic PPU (NewPPU=0), readonly ROM+canonical movie archives were reopened without changing any recorded original pixels or source registers:

| Original archive | Exact original frame range | Original source files verified |
| --- | --- | ---: |
| Stage354 | 495–519 | 32/32 |
| Stage350 | 520–544 | 32/32 |
| Stage359 | 545–559 | 22/22 |
| Stage351 | 560–584 | 32/32 |
| **Total** | **90 consecutive authentic original RGB frames** | **118/118** |

Each of the four archive ZIP CRC checks and owner-private independently pinned source manifest SHA256 checks passed. The **complete 261-frame Stage335 CPU and Stage341 native PPU original traces** were identical across all four independently recorded original captures and matched the prior original seals. The original indexed palette evidence included **12 complete index planes and 540 independently RGB/index-matched probes**. No original ROM/FM2 included in the source-derived ZIPs.

## Three previously unevaluated cross-archive image joins

Frozen image masks: exact original environment source ROIs, 49 signed vertical offsets −24 to +24, pixel mismatch <= 0.16, best vs next-best gap >= 0.045, with independent confidence categorization (four-of-four, three-of-four, conflict, inconclusive).

| Authentic original adjacent pair, across separately archived captures | RGB displacement | Frozen four-region confidence | Original first second-phase `$2005` Y modulo-240 change | Agreement |
| --- | ---: | --- | ---: | --- |
| 519 → 520 | **+3 px** | strict 4/4 | −3 | yes |
| 544 → 545 | **+4 px** | strict 4/4 | −4 | yes |
| 559 → 560 | **+5 px** | strict 4/4 | −5 | yes |

**3/3 strictly qualified source joins match independently pinned original first `$2005` scroll step**; 0 ambiguous, 0 conflicts, 0 register unsupported, 0 source-register contradictions. This establishes a finite pixel displacement relationship at these three interfaces. It does **not** prove universal car/camera acceleration, vehicle speed, perspective geometry, road collision or dot-level hardware timing.

## Exact finite +3 to +4 transition within previously published Stage350 source

The separate original 520–544 interval contains **24 adjacent pairs**. Reclassification with the same four region confidence rules yielded **19 strict four-region**, **5 exactly three-region**, **0 conflict**, **0 ambiguous** image shifts, with 24/24 independently authenticated original first-Y source PPU register matches:

| Original pair-start range | Adjacent pair | Qualified image shift | Pair count |
| --- | --- | ---: | ---: |
| 520–526 | 520→521 through 526→527 | **+3 px** | 7 |
| 527–543 | 527→528 through 543→544 | **+4 px** | 17 |

The finite scene displacement first changes from +3 to +4 between the **526→527** and **527→528** pairs; **527→528 is the first +4 observation** under fixed masks. This is an original-data retrospective localization, not a prospective validation of any cause.

Earlier scientific result boundaries remain fixed: Stage355 380–404 full source RGB image-motion gate **FAILED/INCONCLUSIVE**, and Stage357 405–419 still has **five original inconclusive image pairs**. Stage359's 545–559 finite +4 result remains unchanged. All general physics/camera claims remain unsupported.

## Owner-private permanent storage

Stage360 created **NO new source ROM/FM2 or RGB capture**; the four original source archives stay in their prior owner-only Drive locations. New private derived evidence (no original NES/FM2/GD RGB images, index planes or raw CPU/PPU trace TSVs) was uploaded and independently re-downloaded with full byte-for-byte SHA/size checks:

- [Private Stage360 derived ZIP (8,437 bytes; 5 derived members)](https://drive.google.com/file/d/1X5oZFE04E9PaC5jLe7C3KJ-GvZ9G8O6Y/view)
- [Private Stage360 numerical aggregate](https://drive.google.com/file/d/1hfUaFM7YupDC-13wa9x5IKep_r8VBBPj/view)
- [Private per-boundary and Stage350 per-pair diagnostics](https://drive.google.com/file/d/10orl4Y6PexHUFSguxssX7Mzy7snNCda8/view)
- [Private four original archive SHA/provenance ledger](https://drive.google.com/file/d/19E_TRIOI3LQo35zDfXsCKUrBiDdmsiib/view)
- [Private five-member derived manifest](https://drive.google.com/file/d/1-tB_5KIeAl8YkYzkRKFnqK5GA5SOm098/view)
- [Private SHA preupload seal](https://drive.google.com/file/d/1TAIr2JyUAe5r2UjDPfSwXmUhBfZuusAC/view)
- [Private Stage360 handoff](https://drive.google.com/file/d/17Llr3MC-XLj_t-fi5dI_-pMU8HdtHOrb/view)

All **seven independent owner-only Drive assets** re-downloaded with exact SHA256 and bytes, archive ZIP CRC and **5/5 internal member SHA256** checked. The standalone private readback receipt stays in `00_Manifest_and_SHA256`. Owner-original SHA values were not copied into this public document.

## Public code/CI

- `tools/audit_private_stage360_bridges.py`: source-authenticated cross-archive auditor (originals required ONLY for owner-local execution), original environment masks, negative/conflicting/unsupported preservation, no private hash constants in code.
- `tests/test_stage360_bridges.py`: **22 fabricated-only regression tests**, no ROM/movie/images or original CPU/PPU traces in public CI.
- `docs/DRIVING_STAGE360_CROSS_ARCHIVE_PROTOCOL.md`: frozen retrospective source joining plan and limitations.
- `docs/stage360_public_aggregate.json`: original source-free numerical totals, explicitly retrospective.

The source-side decoding of UTF8 BOM TSVs was corrected before final archival and result publication; the frozen scoring masks/thresholds were not altered. Exact-head Native Core CI result must be verified on the final public report commit before labeling Stage360 CI successful. Draft PR #99 stays Draft and `main` stays unchanged.

Possible future Stage361: independent prospective source capture beyond the existing 380–640 full CPU/native PPU trace window, first preregistering extension format and negative controls; OR build a bounded state-machine for these finitely observed nonuniform scroll modes without claiming general road/car physics. Maintain owner-only evidence archive and SHA readback.
