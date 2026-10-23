# Stage 346 — original-source scroll-window preflight and private RGB replay preparation

**Historical pre-capture checkpoint:** this document describes the trace-only stage and its temporary Lua 5.1 blocker. The blocker was resolved and a new authentic RGB replay of frames 445–469 succeeded. For the verified later result, see [Stage346 original RGB scroll join](DRIVING_STAGE346_ORIGINAL_RGB_SCROLL_JOIN.md). The earlier statements here that no new RGB data had been captured are explicitly **superseded**, not current project status.

## Confirmed sources

- Previously authenticated Stage344 read-only FCEUX 2.6.5 classic PPU (NewPPU 0), original FM2 and ROM, 261 CPU/PPU source frames 380–640.
- Independently owner-sealed Stage335 CPU and Stage341 native-PPU TSV digests; full original trace files remain owner-private in the Project Evidence Archive.
- Owner-private Stage344 completion and archive readback receipt with SHA-256 and ZIP CRC.
- ROM-free instrumented FCEUX Stage341 build artifact (GitHub Actions #40029643206, artifact #12535080120), downloaded and SHA-256 verified in a private workspace.
- Canonical owner-held ROM and FM2 were fetched from private Google Drive and their independently recorded SHA-256 values matched.

## New original-source trace findings (no new RGB frames)

Four **non-overlapping** 25-frame source windows were preflighted against the original CPU/PPU traces. All 100 source frames had the **first second-phase $2005 vertical input equal to live RAM $0D** and the corresponding Y field of classic native PPU TempAddr at line zero, with no intervening $2005/$2006 writes. All four windows' later second-phase $2005 values were constant across 24 consecutive transitions.

| Source interval | 0 | -1 | -2 | -3/-4 | <= -5 | Source RAM $0D writes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 445–469 | 0 | 18 | 6 | 0 | 0 | 25 of 25 frames |
| 470–494 | 0 | 0 | 23 | 0 | 1 | 25 of 25 |
| 520–544 | 0 | 0 | 0 | 24 | 0 | 25 of 25 |
| 560–584 | 5 | 0 | 2 | 1 | 16 | 20 of 25 |

Categories are modular **signed 8-bit register differences**. They are not measured display-pixel distances or car/camera speed, particularly across scroll wrap or scene transitions. The 470–494 interval includes one -18 register change; we must not silently describe this as 18 pixels of background motion.

This is **100 verified CPU/PPU source frames and 96 adjacent register comparisons**, but **zero new independent RGB frames** outside the earlier 420–444 interval. Therefore Stage345's 24/24 pixel/register correlation is **not yet generalized**.

## New public ROM-free functionality

- `tools/audit_private_stage346_scroll_windows.py`: owner-local sealed SHA-256 and read-only completion gate, CPU/native source frame-order and scroll checks, and numeric-only interval categories; it never outputs original source values, event cycles, ROM/FM2, pixels or private digests.
- `tools/prepare_private_stage346_rgb_capture.py`: exact private Stage344 Lua source hash guard and strict replacement of only authenticated 420–444 selectors with a chosen 25-frame target, plus three correctly positioned palette snapshots. It refuses changes to the sealed source, unsupported windows, overwriting any capture, or missing FCEUX source contracts.
- `tests/test_stage346_scroll_windows.py`: 20 fabricated-only regressions for register classification, wrap, mismatched source, missing native PPU anchors, later-scroll phase changes and private Lua selector integrity.
- `docs/stage346_public_aggregate.json`: safe aggregate only, with explicit unproven pixel-motion, dot timing and vehicle-physics flags.

The first planned RGB extension is **445–469** (register steps -1 or -2 only). Later windows 470–494 and 520–544 are intentional stress tests for discontinuities and larger steps, not selections presumed to support the hypothesis.

## Current runtime blocker and storage

The exact instrumented FCEUX binary was restored from the successful GitHub Actions build artifact; however the current Debian runtime has no `liblua5.1.so.0`. Consequently **the instrumented emulator cannot yet perform the new original RGB replay in this workspace**. Do not call the prepared Lua file an executed capture. The ROM-free executable build artifact must be persisted in the owner-private Drive 07_Builds_and_Test_Artifacts folder before GitHub's short artifact retention period expires.

Private Stage346 Lua capture preparation, original-source derived aggregate, checksum/provenance manifest and handoff belong in the Project Evidence Archive. Preserve original owner-private ROM/FM2 and traces; never publish them in GitHub/CI. Keep PR #99 Draft; do not alter gameplay camera or physics based on these source register steps.

## Stage347 gate

Restore independently identified compatible Lua 5.1 runtime; replay chosen 25-frame window privately using the pinned ROM/FM2/FCEUX binary and exact Lua source; archive raw RGB/PPU/CPU in owner-only Drive; independently download and SHA-256/ZIP CRC verify; then use the masked pixel score with a wider validated search range and careful treatment of scene changes. Fail closed on ambiguous/blank regions, discontinuity or original-source mismatch. Do not extrapolate the Stage345 one-pixel law in advance.
