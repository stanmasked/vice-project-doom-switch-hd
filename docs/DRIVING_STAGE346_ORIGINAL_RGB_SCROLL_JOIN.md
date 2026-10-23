# Stage 346 — authenticated original 445–469 RGB / classic PPU scroll correlation

## Real original-source replay confirmed

A new owner-local, read-only FCEUX 2.6.5 **classic PPU** (`NewPPU 0`) replay of the canonical NTSC ROM and the full taotao FM2 (43,652 inputs) successfully captured **25 consecutive original XBuf RGB images, frames 445–469, native 256×240**. This stage is separate from the prior Stage344/345 original images 420–444.

Original-image capture requires Lua 5.1. The ROM-free `Stage346 Lua 5.1 ROM-free runtime packaging` workflow #40038330734 passed; its only artifact was the public Lua 5.1 shared library, ABI-checked with a fresh interpreter state and then owner-locally loaded into the previously verified Stage341 instrumented FCEUX executable. No original ROM, FM2, gameplay pixels or raw traces were used by GitHub Actions.

Full new-session Stage335 CPU and native classic Stage341 PPU traces were reauthenticated by SHA-256 against their **independent prior owner-private seals**. Both are **byte-for-byte identical** to the original Stage335/341 traces. The original movie completion marker also matched its sealed previous identity. 25 GD RGB frames, three full 256×240 indexed palette planes (445, 457, 469), and 150 independently sampled RGB/palette probes were checked.

## Independently verified image displacement

The source-hash-gated Stage344 RGB pixel-motion auditor was run on the **new** 445–469 manifest and frames with two externally pinned Stage335/Stage341 digests; all four physically distinct non-vehicle/non-HUD environment/marking texture bands independently agreed in all 24 adjacent comparisons. The maximum best-shift error fraction was 0.0022.

| Consecutive 445–469 transition | Measured original screen displacement | First second-phase $2005 Y difference | Pairs |
| --- | --- | --- | ---: |
| 18 pairs | +1 RGB display pixel downward | -1 signed 8-bit step | 18 |
| 6 pairs | +2 RGB display pixels downward | -2 signed 8-bit steps | 6 |

**24/24 original pixel/register comparisons agree.** All 25 source frames' first $2005 vertical bytes equal live RAM $0D and the classic PPU line-zero TempAddr vertical bits. The later $2005 phase stays constant across 24 transitions. The pattern differs from the prior Stage345 420–444 interval (11 zero-shift and 13 +1-pixel pairs), providing an independently replayed broader visual witness.

This is **two finite observed windows**, not proof of a general camera speed law, vehicle motion model, road perspective, collision or exact hardware PPU dot/scanline phase. A register jump of -18 in an as-yet **unrendered** follow-up window must not be extrapolated as 18 physical pixels of movement.

## Strictly private owner-held source and durable archive

The new owner-private original archive is `Stage346_original_445_469_RGB_CPU_PPU_private.zip` (2,145,078 bytes; 36 ZIP members), including 32 source-manifest-authenticated members, private Lua capture source, private aggregate and local execution log. ROM and FM2 are excluded and stay in their **canonical original Drive folder**, unchanged.

- New owner-private original capture ZIP: https://drive.google.com/file/d/1hfVZYeBSwIERdx1D5XW6pIZxtT0wos4K/view
- Private 32-file digest/source identity manifest: https://drive.google.com/file/d/1RX5lSq2szgeVW2tzVrFivqI-MHHH6Z73/view
- Owner-local source-derived aggregate: https://drive.google.com/file/d/1sBAIOt14XErln9JeSNmgMMZaWhJoSQbh/view
- Previous independent archive receipt: https://drive.google.com/file/d/11jxurUzUnhZ5u5Vem1YN-CERaT6gRfrh/view
- Persistent owner-private pinned FCEUX toolchain: https://drive.google.com/file/d/1nCLkiWPqxL0j0cPwWbNNRrcaKpALY-3l/view
- Persistent public-license Lua 5.1 runtime library archive: https://drive.google.com/file/d/13Apr-UMl6vDiHkEAp1PmVdEMzFcRvNl4/view

The five new original source/manifest/report/runtime Drive uploads were **independently re-downloaded**, size and SHA-256 compared against private workspace bytes, and ZIP CRC and all 32 manifest-listed original member SHA-256 values rechecked. Drive metadata reports private (not shared). No proprietary input was committed to GitHub or exported to public CI.

## Public code and verification contract

- `tools/audit_private_stage346_original_rgb_scroll.py`: private-input 445–469 same-source RGB, CPU, native PPU cross-check with independently pinned original manifest and prior Stage335/341 SHA-256. Public program emits only bounded aggregate counts/boolean evidence flags; an absent, tampered, ambiguous or contradictory sample fails closed.
- `tests/test_stage346_original_rgb_scroll.py`: 13 **fabricated-only** regressions covering +1/+2 pixels, old/latest-scroll ambiguity, wraps, missing/duplicate frames, unsupported displacement, contradictory source values and false vehicle-physics inferences.
- `docs/stage346_original_rgb_public_aggregate.json`: sanitized report without original screenshots, cycles, bytes, register values or hashes.

Native Core CI is ROM-free, and its result must be checked on the **exact final code head**. It cannot replace owner-local original input authentication. PR #99 remains Draft, main unchanged.

## Next Stage 347

Re-use the now-persistent owner-private pinned FCEUX/Lua toolchain to capture **470–494** as a deliberate stress test of signed Y register steps, especially the single source-observed -18 discontinuity. Treat new scenes, flat masks, jumps outside validated shift search and rendering mode changes as inconclusive, not as a general camera-speed increase. Independently verify source/frame hashes and private Drive readback before making further physics or road-rendering decisions.
