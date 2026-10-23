# Stage 342 — independently verified classic PPU scroll chain

## Authentic inputs and replay provenance

This stage **analyzes and independently revalidates existing Stage 341 owner-private original-source captures**, without claiming an additional FCEUX replay. The raw CPU witness is the sealed same-session Stage 335 event trace (21,398 rows). The native classic-core FCEUX v2.6.5 witness contains 312,189 rows. Both are from the original read-only FM2 replay at 261 aligned game frames, 380–640, with `NewPPU 0` and the original ROM. The auditor requires caller-supplied complete SHA-256 digests from the owner-private manifest; the digests, gameplay register values, and controller inputs are **not committed to GitHub**. Original raw source files stay in the private Google Drive archive.

## New source-backed findings

1. **Exact observed CPU timestamp alignment for PPUADDR:** for each of 3,048 second-phase `$2006` writes, the classic FCEUX native timestamp equals `(Stage335 global CPU cycle − Stage335 frame_begin cycle)` in the same frame, and the full 14-bit PPU address also agrees. There are zero mismatches.
2. **Original RAM `$0D` source of first vertical scroll pair:** the first second-phase `$2005` event equals its live RAM `$0D` value in each of 253 frames where such a pair occurs. This distinguishes the initial vertical scroll setting from a later scroll write in the same frame, which may reset the latch value and **must not be mistakenly included** in the source-of-scroll count.
3. **Direct classic PPU temporary-state witness:** the native `TempAddr` vertical bitfields sampled at `legacy_line_start` of renderer line zero agree with the first `$2005` second-phase write in all 253 eligible frames. In each case the CPU scroll write precedes the native sample, with **no intervening `$2005`/`$2006` CPU bus writes**. The expected vertical `t` bits are `((scroll_y & 0xf8)<<2)|((scroll_y & 7)<<12)` masked by `0x73e0`. This verifies the software-to-emulator temporary-address chain, **not** output pixels.
4. **Rendering path transitions:** the 261-frame capture includes 60,480 classic PPU vertical increments and 60,480 horizontal reloads, organized into 240 lines each for 252 frames. Nine consecutive frames contain neither set of classic address transitions; eight of those frames also have no `$2005` writes. The classic core still runs its line-boundary CPU slices in these frames; absence of address updates is consistent with the rendering-enable condition and does not prove the game's motive for disabling rendering.

The source-free test module `tests/test_stage342_scroll_chain.py` includes negative cases for corrupted CPU/native clock alignment, mismatched native addresses, mismatched RAM `$0D`, wrong `TempAddr` vertical bits, intervening PPU register writes, duplicated/missing frame anchors, invalid purported dot positions and bad source digests. All 11 tests passed locally before the public commit. CI must separately verify the exact committed head.

## Evidence limits

- `legacy_line_start` is a **classic FCEUX software renderer phase**, not an independently validated hardware PPU dot. The event timestamp is a CPU-cycle-relative emulator clock, not a full physical scanline/dot trace.
- This data confirms the first Y-scroll input reaches the classic PPU **temporary** address, but does **not** prove the final on-screen pixel scroll, effects of mid-frame v reload, road perspective geometry, camera speed or collision physics.
- No same-frame RGB/road-pixel comparison was performed at Stage342; Stage343 should plan an independently anchored original-source image capture and raster-region comparison, while preserving original native-core mode and all private source identities.
- Keep PR #99 Draft; do not merge original assets or original traces into public GitHub.

## Private reproducibility

```shell
python tools/audit_private_stage342_scroll_chain.py \
  --cpu /private/stage341_same_session_stage335_cpu_events.tsv \
  --native /private/stage341_classic_refreshaddr.tsv \
  --cpu-sha256 "$PRIVATE_CPU_TRACE_SHA256" \
  --native-sha256 "$PRIVATE_NATIVE_TRACE_SHA256" \
  --output /private/stage342_aggregate.json

python -m unittest discover -s tests -p 'test_stage342_*.py' -v
```

All outputs are only counters/booleans; the private SHA-256 values belong in the owner-private manifest. The original FCEUX, original FM2 and raw gameplay data must remain outside public GitHub.
