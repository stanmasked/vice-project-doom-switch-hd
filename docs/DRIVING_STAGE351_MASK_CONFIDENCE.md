# Stage 351 — original RGB 560–584: strict vs exploratory mask confidence

## Original source replay

A new owner-private read-only FCEUX 2.6.5 classic PPU capture of the original NTSC Vice: Project Doom ROM/FM2 produced 25 consecutive native 256×240 XBuf RGB frames 560–584. Complete CPU/PPU event streams are byte-identical to prior Stage335/341 source seals; the completion marker, three full indexed palette planes, 150 individual RGB/index probes, and all 32 source files are independently SHA-256 checked.

This window deliberately stresses the Stage350 modulo-240 vertical background-scroll model in the presence of a stationary pause and larger moves. Existing Stage344 four-region masks were applied **without modification first**, across 24 adjacent image pairs.

## Preregistered fixed-mask result — 23/24, one inconclusive

Four independent texture regions: left environment, right environment, left road marking, right road marking. The original preregistered four-band scoring pipeline accepted **23 of 24** transitions and matched the modulo-240 first-scroll delta on all 23. **One transition remained inconclusive**, not mismatched: both environment regions uniquely selected a +8-pixel vertical shift with zero RGB error, but the repeated road-marking texture could not distinguish alternate shifts (notably a 32-pixel alias). The proper primary-gate result is **23 qualified, 1 inconclusive**.

## Secondary adaptation — exploratory only

After seeing the ambiguous marking, we split the two already validated non-vehicle/non-HUD **environment** parent regions into four nonoverlapping upper/lower windows. All 24 original transitions then independently scored a unique shift in each of these four subwindows; all 24 agree with the modulo-240 first `$2005` input deltas.

| Additional observed motion | Adjacent pairs |
| --- | ---: |
| 0 pixels | 5 |
| +2 pixels | 2 |
| +3 pixels | 1 |
| +5 pixels | 15 |
| +8 pixels | 1 |
| **Total** | **24** |

**Critical inference boundary:** secondary masks were selected *after* inspecting the one ambiguous interval; their agreement is **exploratory**, not an independent prespecified 24/24 replication. Do not silently replace the initial 23/24 confidence finding with the adapted 24/24 result. A future independent new frame window should test the changed masks as predeclared before any further model generalization.

## Source storage and privacy verification

- [Owner-private original Stage351 capture ZIP](https://drive.google.com/file/d/1KvU6YXl1BVCXV-HrZARFc_0_QQh4hTxr/view), 2,155,053 bytes, 38 ZIP members. Contains 32 original source members and six owner-only service/diagnostic files; ROM and FM2 excluded.
- [Owner-private source SHA manifest](https://drive.google.com/file/d/1HwphjUF9g04AB8FrNyWu3Rid2xPnjlhz/view).
- [Private dual-gate aggregate](https://drive.google.com/file/d/1gFZlF1_4s9EuST3k9hyXKSd7rdCxUF0g/view).
- [Private independent Drive readback record](https://drive.google.com/file/d/1Ug6a2U9SoKgRuuYfSGXJp-xhiXmBWTIA/view).

All four primary stored evidence files were downloaded from owner-only Google Drive and their SHA-256 matched the pre-upload source. ZIP CRC passed and all 32 per-file source SHA-256 checks passed. Raw owner/private register rows, pixels, Lua and source hashes remain excluded from public GitHub and public CI.

## Public ROM-free contract

- `tools/classify_stage351_motion_confidence.py` explicitly distinguishes previously fixed four-band evidence from later posthoc environment-submask evidence, requires complete 24-pair count and refuses fabricated contradictions. The classifier takes numerical score summaries, **not original raw data**, and does not by itself prove source identity; the original-source SHA audit occurs separately in the owner-local pipeline.
- `tests/test_stage351_motion_confidence.py`: 12 manufactured-only tests reject tampered, missing, flat, contradictory, unsupported or improperly promoted secondary evidence.
- `docs/stage351_public_aggregate.json`: safe aggregate with both provenance tiers and no proprietary source assets.

## Next scientific check

Conduct a new owner-local original RGB replay using the *new* four environment submasks declared in advance; verify CPU/PPU source seals and archive results back to private Drive before claiming a broad scroll-rendering law. Preserve separation between image motion, PPU register state and actual automobile/road physics. PR #99 remains Draft; main unchanged.
