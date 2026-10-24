# Stage359 — preregistered authentic original 545–559 gap holdout result

## Preregistered before original FCEUX source access

Protocol [`docs/DRIVING_STAGE359_GAP_PREREGISTRATION.md`] was committed at GitHub SHA `caad7b85b06b5857f39625a5c021e9b4c3c8cde8` before any first new original source frame was captured. Exact previously unused original interval **545–559**, fifteen consecutive original native RGB frames and **fourteen** adjacent pairs; four fixed half-open environment masks used by Stage353/354/357 (left x0–52 and right x195–255, y20–98 and y98–175), signed image offsets **-24 through +24**, max pixel mismatch **0.16**, min best/runner-up confidence gap **0.045**, categories: strict 4/4, qualified 3/4, confident conflicts, inconclusive. No post-capture rule changes. All source audit and fabricated-only tests committed before FCEUX original replay; a subsequent correction to a *synthetic test import path* changed no thresholds, algorithm, original-source selection, or source measurements.

## Authenticated owner-private source and original result

Original owner-private NTSC Vice: Project Doom NES ROM and canonical taotao FM2 replayed **read-only** under real FCEUX v2.6.5 classic PPU (NewPPU=0). Completed FCEUX replay original frame range 380–640 with same read-only identity marker, full 261-frame Stage335 CPU and Stage341 classic native PPU traces byte-identical to prior independently held SHA seals. Captured **15 consecutive native 256×240 RGB GD frames 545–559**, **3 complete indexed palette planes at 545/552/559** and **90 RGB/index probes**; all original files and samples validated. Each of the **22 original source members** SHA-pinned and later revalidated independently after Drive recovery.

| Original source evidence metric | Result |
| --- | ---: |
| Consecutive original RGB frames | **15** |
| Adjacent original image transitions | **14** |
| Unique whole RGB images | **15** |
| Single-color / byte-identical adjacent images | **0 / 0** |
| Confident independent four-mask (strict 4/4) image shifts | **9 / 14** |
| Confident independent three-mask (3/4) image shifts, fourth weak | **5 / 14** |
| Confident mask conflicts / image-inconclusive pairs | **0 / 0** |
| Qualified original image displacement distribution | **+4 pixels × 14** |
| Independently verified signed first second-phase $2005 vertical Y delta, mod240 | **−4 × 14** |
| Qualified source image/scroll matches | **14 / 14** |
| Qualified source image/scroll contradictions | **0** |
| Qualified image source-register comparison unsupported | **0** |
| Frames lacking first authenticated CPU $2005 source anchor | **0 / 15** |
| Native classic PPU line-zero mask zero | **0 / 15** |
| Verified CPU/native PPU full original frame anchors | **261 / 261** |

**Scientific interpretation:** This held-out finite original scene segment confirms **background/texture image displacement +4 native pixels** in all 14 adjacent original pairs, supported by strict 4/4 confidence on 9 pairs and 3/4 confidence on the remaining 5, matching the independently authenticated original PPU first vertical $2005 source values with opposite signed −4/240 step. Earlier Stage354 on a distinct finite segment had +3 pixels; the stages do not prove a universal vehicle speed, physical game-camera law, collision/road perspective or NES PPU dot timing. No hidden sourcing of absent CPU writes; none were absent in this segment.

Stage355 380–404's **FAILED/INCONCLUSIVE** scientific image-motion gate remains unchanged. Stage357 405–419 has 9 strict **zero-pixel** image/register matches and **5 inconclusive** source image pairs; its five inconclusive pairs are not rescued by Stage359. Stage358 remains retrospective onset analysis, not a new heldout test.

## Private evidence archive and independent Google Drive readback

Permanent, owner-only Google Drive Project Evidence Archive:

- [Stage359 original source RGB/CPU/native PPU evidence ZIP, 2,108,558 bytes, 27 members](https://drive.google.com/file/d/1eM3MdCYHs1xGdaI-nip6Muoerlya_P27/view)
- [Original exact 22-member SHA-pinned manifest](https://drive.google.com/file/d/1vsWzZBynvsMFZ85EaZt45wKD7Mv62PlA/view)
- [Private source aggregate](https://drive.google.com/file/d/1VEC6uQbAgoTTbexCN7gkxyYCvTAPb2H1/view)
- [Private per-pair original masks, confidence and scroll diagnostics](https://drive.google.com/file/d/1G3tDiIjUSSoP8hPQgTUxo01iQwu8gJls/view)
- [Original source preupload SHA/ZIP seal](https://drive.google.com/file/d/1aKEIK7vc8gWeJk9mlkwLxu6XYcr1wtdd/view)
- [Independent six-file postupload SHA, CRC, all 22-member recovery receipt](https://drive.google.com/file/d/1YvvefFXtp30Mu8hSqIQ3G96wJu2shZF_/view)
- [Private Stage359 handoff](https://drive.google.com/file/d/1dSQ2-yKHHftsB80XjiU70wGlSlyt9xPJ/view)

**6 owner-only objects** uploaded, explicitly verified as private, independently re-downloaded and all full-file SHA256 and exact lengths compared against local source. The downloaded ZIP passed CRC and **22/22 original per-file SHA checks**; full original NES ROM and canonical FM2 were deliberately excluded from the derived archive. The source capture Lua is preserved inside owner-private archive only, never in GitHub or public CI.

## Code, tests and CI

Public source-safe files:
- `tools/audit_private_stage359_gap_holdout.py` — fixed confidential-original-data audit; 4 source ROIs with fail-closed confidence categories.
- `tests/test_stage359_gap_holdout.py` — **17 fabricated-only regression tests** including missing-write rejection, conflicting confident bands, 4/4, 3/4, inconclusive, no imputed Y values and exact 15-frame restrictions.
- `docs/DRIVING_STAGE359_GAP_PREREGISTRATION.md` — immutable original independent window contract before source replay.
- `docs/stage359_public_aggregate.json` — nonreversible numeric summary, no original pixels, full trace rows, ROM/FM2 or owner-private file digests.

The initial test import of the source auditor was incorrect, causing Native Core CI #40048112699 to fail *in synthetic test collection*, not original-source authenticity or native physics; corrected the import with commit `227f42c5e755abecef44f94f00c8a239e97e8b11`. [Native Core CI #40048265246](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/40048265246) **SUCCESS** on that source+test revision. The exact final results-document head GitHub Actions must be checked separately and not presumed green.

Draft PR #99 remains open; `main` unchanged. Next Stage360 can investigate the transition from +3 shift to +4 shift or cross-boundary camera/scroll registers as a *separately preregistered fresh-source question*; do not reinterpret fixed earlier results.
