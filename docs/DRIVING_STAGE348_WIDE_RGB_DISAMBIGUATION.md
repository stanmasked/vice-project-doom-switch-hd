# Stage 348 — wide native RGB verification of the Stage347 scroll anomaly

## Independently authenticated original source

The one anomalous adjacent pair is part of the genuine Stage347 owner-private 25-frame capture (original frames 470–494, native 256×240 RGB, FCEUX v2.6.5 classic PPU, original owner-held ROM and read-only FM2). No new ROM run was required: this stage rescored the **previously sealed original RGB**, CPU and native PPU evidence, re-verifying the Stage347 member and original archived source identities and the Drive readback receipt.

Stage347 showed 24 background motions of +2 display pixels per frame; the first second-phase `$2005` vertical Y input steps by −2 in 23 of the 24 transitions, but **one original transition steps −18 while the image still moves +2 pixels**. Stage348 tests whether this is an alias caused by Stage344's narrow displacement search −4 to +4.

## New wider pixel scoring

An independent private experiment compared **all 49 signed vertical offsets from −24 to +24 pixels** in each of four non-sprite/non-HUD image regions. The original image pair was authenticated with stored SHA-256 per file before calculating mismatches.

| Original RGB candidate region | Best visible shift | RGB mismatch at best shift | RGB mismatch at +18 shift |
| --- | ---: | ---: | ---: |
| Left environment | +2 px | 0.0000 | 0.4382 |
| Right environment | +2 px | 0.0000 | 0.3860 |
| Left marking | +2 px | 0.0000 | 0.2944 |
| Right marking | +2 px | 0.0000 | 0.2944 |

Every region selected **exactly +2 pixels as its unique best match**; the runner-up was unambiguously worse. Thus +2 is not a search-window artifact and interpreting the −18 source register jump as an 18-pixel background movement is directly contradicted by the original raster sample. This conclusion is **limited to the one original transition**; it does not identify the cause of the −18 register change or prove general road/camera speed, a hardware PPU dot, vehicle physics, collision, or level geometry.

## Auditors, testing and privacy

- `tools/audit_private_stage348_wide_displacement.py` verifies the owner-private sealed Stage347 manifest and prior Stage335/341 CPU/PPU source identity, isolates the unique exceptional pair, and enforces an unambiguous four-region ±24 pixel score. It fails closed on source integrity changes, flat/periodic textures, an unobserved displacement or unexpected alternate result.
- `tests/test_stage348_wide_displacement.py` contains **9 fabricated-only regressions**, including real synthetic +18 movement, 16-pixel repeating textures, flat RGB, invalid region geometry and a malformed/truncated source.
- `docs/stage348_public_aggregate.json` records only safe aggregate observations and evidence limits. Original ROM/FM2, RGB screenshot data, register bytes, sealed private hashes and raw trace rows are **never committed to public GitHub or public CI**.

## Private persistent evidence

The canonical owner-only original-source ZIP is the verified Stage347 Drive archive:

- [Stage347 original RGB/CPU/PPU ZIP](https://drive.google.com/file/d/1khw-pYXTVDGbmimSny4QlZKIwI6P9osO/view)
- [Stage347 original manifest](https://drive.google.com/file/d/1AZeEyGd0Iq8eEzcezDXIvfxxhiWT6qtI/view)
- [Stage347 owner-only completed readback receipt](https://drive.google.com/file/d/1Lf_q5sM6TwrC-NxAy07FNkgDXNysoiNL/view)

The derived Stage348 wide-offset score belongs in the project's owner-private `03_Aggregate_Reports` archive; the source originals must not be moved to the public repository. PR #99 remains Draft, main unchanged.

## Next research gate

Investigate effective classic-PPU rendering address and nametable/fine-Y reload at the one exceptional pair and nearby windows. Correlate it with independently authenticated RGB before changing HD background projection or vehicle physics. New full-width frame captures and the corresponding original source fingerprints remain owner-private.
