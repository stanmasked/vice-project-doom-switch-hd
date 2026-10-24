# Stage354 — independently captured original RGB gap-window result

## Preregistered source and frozen criteria

The owner-local original-source audit was committed before new RGB frames were captured: `tools/audit_private_stage354_gap_holdout.py`, 17 synthetic ROM-free regressions in `tests/test_stage354_gap_holdout.py`, and immutable protocol `docs/DRIVING_STAGE354_PREREGISTERED_GAP_PROTOCOL.md` (commit `daf325993bf0d93972a323401be6627f7029b559`). Original frame window **495–519** was selected in advance to fill an otherwise unsampled gap between genuine previously archived 470–494 and 520–544 windows. No region boundaries, shift limit or confidence thresholds were changed during or after replay.

After this preregistration, an owner-private read-only FCEUX v2.6.5 classic-PPU (NewPPU 0) replay of the canonical NTSC Vice: Project Doom ROM and taotao FM2 captured **25 consecutive native 256×240 XBuf RGB frames 495–519** and indexed palette planes 495, 507, 519. All **150 original RGB/index probes** and the three full palette planes passed. The complete CPU Stage335 and native PPU Stage341 traces reproduced independently sealed prior original witness SHA-256 files, and the owner-private completion marker matched the sealed read-only ROM/FM2 replay.

## Original source observation — 24/24 strict original four-mask agreement

The identical four environment-only source RGB rectangles and thresholds from Stage353 were prespecified:
`(0,52,20,98)`, `(0,52,98,175)`, `(195,255,20,98)`, `(195,255,98,175)`; all 49 vertical shifts −24…+24 independently scanned per region; best mismatch ≤0.16, runner-up minus best mismatch ≥0.045.

| Preregistered evidence tier / source observation | Adjacent pairs |
| --- | ---: |
| All **four** independently confident image masks select +3 pixels | **24** |
| Only three confident image masks select common displacement | 0 |
| Conflicting confident mask predictions | 0 |
| Insufficient confident independent image regions | 0 |
| Qualified image displacement agrees with inverse first second-phase $2005 Y **modulo 240** | **24/24** |
| Qualified image/PPU register contradictions | **0** |

Every one of the 24 original observed image transitions shows **+3 native display pixels** vertical displacement in the four preregistered environment-only candidate regions, matched to the source scroll-register delta. This confirms the model in one finite unseen source interval; it **does not** establish general game camera velocity, vehicle physics, collision, road-perspective geometry or precise NES hardware PPU dot timing.

The measured interval fills the source-image gap 495–519 without extrapolating from 470–494 or 520–544. The separate, formerly untouched original frames 545–559 remain outside the selected 25-frame captures and are a candidate for later preregistered work.

## Owner-private original evidence and recovery audit

The canonical owner-only Drive archive contains 25 authentic source GD image files, private authentic CPU/PPU event traces, three full indexed palette planes, 150 independent palette/RGB probes, the read-only completion marker, manifest, original Lua capture and local runtime record. It **does not contain any original ROM or FM2 copy**.

- [Stage354 owner-private original ZIP](https://drive.google.com/file/d/1XgHWcahzY2lZhaWm8lHE8haDzucDTrcm/view): 2,148,202 bytes, 37 ZIP members.
- [32-source-member owner-private original manifest](https://drive.google.com/file/d/1oM7bMjHx9wihhys2WewVUA0VAN2C8t1x/view).
- [Owner-private authentic aggregate](https://drive.google.com/file/d/1_dfpB8YbDkz26fz-Qb3dFUB7J7I1aPwx/view).
- [Private per-pair confidence diagnostics](https://drive.google.com/file/d/1knRg7KS-0ZBegytnWN8RZFbUb2YQYanZ/view).
- [Private preupload source seal](https://drive.google.com/file/d/1bQ53eWCrCdZZkPyLllwaiEOClSrHUKfA/view).

All five main assets were separately downloaded back from owner-only Drive and their SHA-256 and size matched the preupload local files; ZIP CRC passed and all **32 of 32 independently manifest-listed source members** matched SHA-256. The separate private readback verification receipt is retained in `00_Manifest_and_SHA256`. Do not publish original pixels, ROM/movie, raw register values, owner-only Lua or private hashes.

## Public ROM-free implementation and CI

- `tools/audit_private_stage354_gap_holdout.py`: source-authenticated original four-region image/PPU verification with independent prior CPU/PPU and fresh manifest pins, unchanged previously frozen four confidence tiers and contradictions retained.
- `tests/test_stage354_gap_holdout.py`: 17 fabricated-only integrity/confidence/negative regression tests.
- `docs/stage354_public_aggregate.json`: source-free observed numeric counts and limits; the protocol is versioned separately from these results.

Keep Draft PR #99 open and do not merge into `main` on this evidence alone. A successful public CI checks ROM-free code only, and exact-head CI must be read after committing the result. Gameplay code, handling/collision, and generalized road geometry are unchanged.

### Following experimental direction

Stage355 should preregister an independent **short source gap 545–559** (15 frames, 14 adjacent pairs) or use a new 25-frame interval 380–404 for a full-length source witness. These are not a 25-frame gap result unless the source actually covers 25 consecutive frames. Both options retain the owner-private evidence and checksum/readback discipline.
