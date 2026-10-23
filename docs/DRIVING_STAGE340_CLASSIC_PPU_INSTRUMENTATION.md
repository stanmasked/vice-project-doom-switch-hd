# Stage 340 — pinned FCEUX v2.6.5 classic PPU diagnostic instrumentation

Stage339 confirmed that the original owner's FM2 is NTSC, explicitly `NewPPU 0`, and contains 43,652 input records. For Stage340, **do not switch to the experimental PPU** to use `newppu_get_scanline()`/`newppu_get_dot()`; their counters belong to a different emulation path.

## Files added

- `tools/generate_stage340_legacy_ppu_patch.py` requires an exact upstream v2.6.5 `src/ppu.cpp` blob and generates a modified **private-local copy**. It inserts guarded probes of the classic path: the second `$2006` write, `Fixit1` (vertical address increment), `Fixit2` (horizontal reload), the classic `DoLine` CPU/renderer boundaries, and a **local FCEUX core-frame ordinal**. The upstream file is not vendored in this repo. The patcher fails when the source blob or anchors differ, and refuses overwriting output.
- `tools/audit_private_stage340_legacy_trace.py` checks the future diagnostic TSV's byte ranges, event types, ordering, core-frame marker coverage, truncation, and optional full-file SHA-256. Its JSON output suppresses all original values and reports that movie-frame alignment, exact PPU-dot timing and actual road scroll are **not** established.
- `tests/test_stage340_classic_ppu.py` uses synthetic FCEUX-shaped source, compiles the injected C++ probe helper with diagnostics disabled/enabled, and checks the strict trace schema. No original ROM, FM2 or gameplay trace is in the tests.

## Private-local recipe (no real ROM or FM2 in GitHub)

```sh
# In a private, user-owned workspace:
# 1) Authenticate your unchanged owner FM2 and ROM, and require NewPPU 0.
python tools/audit_private_stage339_core_mode.py \
  --movie "$PRIVATE_FM2" --source-sha256 "$PRIVATE_FM2_SHA256" \
  --expected-frames 43652

# 2) Recover exact FCEUX v2.6.5 source in a private non-GitHub location.
#    Verify the tagged original before modification.
python tools/verify_stage339_legacy_ppu_source.py \
  --ppu-source "$PRIVATE_FCEUX_SRC/src/ppu.cpp"

# 3) Generate an opt-in modified local copy; do NOT overwrite upstream.
python tools/generate_stage340_legacy_ppu_patch.py \
  --upstream-ppu "$PRIVATE_FCEUX_SRC/src/ppu.cpp" \
  --output "$PRIVATE_FCEUX_SRC/src/ppu.stage340.cpp"

# 4) In a separate private build tree, replace src/ppu.cpp with the generated
#    bytes and explicitly compile with -DVPD_STAGE340_DIAGNOSTICS.
#    Compile and confirm the instrumented binary identity before use.
#    Set VPD_STAGE340_TRACE_FILE to a NEW absolute path outside public Git.
#    VPD_STAGE340_MIN_CORE_FRAME and MAX_CORE_FRAME default to 380 and 640.
#    Existing trace destinations are NEVER overwritten.

# 5) After a successful read-only original FM2 replay, calculate raw SHA-256.
python tools/audit_private_stage340_legacy_trace.py \
  --input "$PRIVATE_STAGE340_TRACE" --sha256 "$PRIVATE_TRACE_SHA256" \
  --first-core-frame 380 --last-core-frame 640 \
  --output "$PRIVATE_STAGE340_AGGREGATE"
```

The core-frame ordinal increments when classic `FCEUPPU_Loop` begins and **must not be asserted equal to the FM2 input frame** without an independent clock/frame correlation. The CPU `timestamp` field is the emulator's own counter, not a calibrated physical PPU dot. `legacy_scanline` is the classic renderer's `scanline` variable. The `renderer_pixel_not_dot` field is reserved with a sentinel value `-1` in this patch because no independent pixel clock is sampled. A `legacy_line_256_cpu_slice` event means the call to `X6502_Run(256)` in `DoLine` returned; it is **not** proof of hardware dot 256.

These probes **do not** sample a genuine hardware PPU raster-dot position and do not independently establish effective pixel scroll, camera speed, road geometry, or driving collision physics. Their purpose is to obtain the previously missing *classic emulator internal-address transition evidence* without altering the original movie's PPU mode. A subsequent source capture must prove timing/frame alignment against earlier sealed Stage335/336 traces and original RGB before drawing game-behavior conclusions.

## Privacy and build restrictions

- The diagnostic code is opt-in, compiled only when `VPD_STAGE340_DIAGNOSTICS` is set. With diagnostics absent, all probe calls become empty inline functions.
- With diagnostics present, **no file is written by default**. An explicit absolute `VPD_STAGE340_TRACE_FILE` path is required. Creation is exclusive (`fopen` mode `wx`); existing files are not overwritten. A hard event cap emits `VPD_STAGE340_TRUNCATED`, which the auditor rejects.
- Do not set this environment variable on public Actions runners. Never upload raw traces or movie screenshots to public GitHub. A separate synthetic-only CI can verify patch generation and compilation of the helper, but cannot claim a successful original replay.
- Capture the exact patched source digest, diagnostic binary digest, source ROM/FM2 IDs, toolchain, frame alignment, output bytes and SHA-256 in the owner-private manifest. Save the raw trace in the private Drive project archive, download it again and verify hash before considering the witness preserved.

### Current evidence state

Stage340 **instrumentation script and source-free tests are implemented**; the patched emulator binary has **not** yet been compiled or run against the original game. Therefore no new original-source raster witness exists yet. The work remains research-only in Draft PR #99.
