# Stage 350 — independently captured original +3/+4 pixel scroll window

## Authentic source and independent replay

A new owner-local **read-only FCEUX v2.6.5 classic PPU** replay of the canonical Vice: Project Doom NTSC ROM and FM2 captured **25 consecutive original XBuf RGB frames 520–544** at 256×240. This is a genuine fourth frame window, independent of the three authenticated RGB windows Stage344/346/347; the game/movie inputs are not publicly distributed.

The newly captured Stage335 CPU trace and Stage341 classic PPU trace were compared by their complete SHA-256 to owner-private prior-stage seals and matched byte-for-byte. The FCEUX `COMPLETE.txt` file matched the prior sealed completion marker. The capture's 25 RGB frames, 3 full indexed palette planes (520,532,544), 150 independently sampled RGB/palette probes, and 4 non-vehicle/non-HUD texture regions were checked by the Stage344 fail-closed visual auditor.

## New out-of-sample measurement

| Original consecutive RGB displacement | Verified pairs | First vertical $2005 / RAM $0D difference |
| --- | ---: | --- |
| Background moves +3 pixels downward | 7 | −3 |
| Background moves +4 pixels downward | 17 | −4 |
| **Total** | **24** | **All 24 match both signed 8-bit and modulo-240 rules** |

Both finite image measurements and matching source register inputs are observed, not synthesized; all four independent masked regions agreed in each pair. This extends the earlier Stage349 model to a higher movement range, but it does not prove exact hardware PPU dots, physical vehicle velocity, collisions, perspective geometry, or all game levels.

### Cumulative verified evidence

| Independently replayed original RGB window | Native RGB frames | Pair count | 240-line scroll agreement |
| --- | ---: | ---: | ---: |
| Stage344/345 — 420–444 | 25 | 24 | 24 |
| Stage346 — 445–469 | 25 | 24 | 24 |
| Stage347/348 — 470–494 | 25 | 24 | 24 |
| Stage350 — 520–544 | 25 | 24 | 24 |
| **Total** | **100** | **96** | **96** |

The preceding 72-pair three-window source-based model was already independently confirmed. The fourth window has its own private evidence ZIP and was not invented by expanding the previous report. The source range between frame 495 and 519 has not been visually sampled in this series, and the 100 verified frames are not one continuous 100-frame capture.

## Private evidence and permanent retention

- [Owner-private original Stage350 FCEUX RGB+CPU+PPU archive](https://drive.google.com/file/d/1cpzEiDQgq8YvnpgAFY7QyHteP4u0QcLA/view) — 2,148,616 bytes, 36 ZIP members.
- [Private source SHA-256 manifest](https://drive.google.com/file/d/1Pm4xV2z5NVDjH6j8J8IGZoSfibijyDCS/view) — 32 original source members pinned.
- [Private numeric measurement aggregate](https://drive.google.com/file/d/1-ynV8Gt4wBqMhHmRjvsTI6CnTkxnppSg/view).
- [Private independent Google Drive readback receipt](https://drive.google.com/file/d/1fsZOKCPfmJjiLzafGK0momrbaxuZQ5ay/view).

Four separately stored assets were downloaded from owner-only Google Drive and their full-file SHA-256 verified against the local pre-upload state. Archive CRC is valid; all 32 original manifest-listed members match independent digests. Four extra ZIP service members were CRC-checked. The ROM and FM2 are not included in the ZIP, and all original source data stays in private Drive.

## ROM-free public implementation

- `tools/audit_private_stage350_out_of_sample.py`: consumes only owner-private externally SHA-pinned RGB, CPU and classic PPU files. Calls the fully authenticated Stage349 prior-window auditor and validates the new 24-pair +3/+4 source-backed baseline. Emits aggregate counts only.
- `tests/test_stage350_out_of_sample.py`: 13 manufactured-only negative/regression tests, including wrong register/image pairing, tampered distribution, unsupported shifts and missing/extra samples.
- `docs/stage350_public_aggregate.json`: anonymized source-backed counters; no ROM, movie, raw pixels, private file digests or registers.

Keep Draft PR #99 open and original game evidence owner-private. A green public CI only verifies source-free contract behavior; no private original captures are run in public GitHub Actions.

## Next check

Acquire new independent original windows around other vertical-scroll transitions (particularly 560–584 with more discontinuities and stationary frames) to test when the modulo-240 rendering model does **not** generalize. Do not alter player car speed/physics or generalized road projection solely from this finite image/source agreement.
