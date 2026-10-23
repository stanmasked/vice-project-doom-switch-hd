# Stage 339 — original FM2 PPU-mode and pinned-core source gate

Stage 338 established a **ROM-free PPU raster-rule model**, not an observation of the actual internal NES PPU address during gameplay. Stage 339 closes a prerequisite before any instrumented FCEUX capture: **do not silently change the PPU core used by the original owner's movie**.

## Authentic source facts

An owner-private full-file SHA-256 check was repeated on the matching original FM2, after which the header was parsed without exporting controller inputs, ROM/FMI identifiers or source hashes to GitHub. The source is FM2 v3, NTSC (`palFlag 0`), and explicitly requests **`NewPPU 0`**, the classic/legacy FCEUX PPU. The input section contains 43,652 records. Neither the FM2 file nor source-private identifiers are in the public branch.

The upstream FCEUX **v2.6.5** tag `ea6ed69b874e3ae94072f1b4f14b9a8f0fdd774b` contains `src/ppu.cpp` at Git blob `aa7502eb956595c29096856ab8beddb5eecc301b`. The source contract checks this exact blob and the expected classic PPU layout. The actual classic implementation uses internal `RefreshAddr`, `TempAddr`, `vtoggle`, `XOffset`, `scanline`, and `g_rasterpos`. By contrast, the public `newppu_get_scanline()` and `newppu_get_dot()` functions read the **different** experimental `ppur.status` core. They are not valid original-mode dot witnesses when the FM2 is recorded with `NewPPU 0`.

Upstream reference: https://github.com/TASEmulators/fceux/tree/v2.6.5

## New tools and checks

- `tools/audit_private_stage339_core_mode.py`: read-only source FM2 inspection, optional full-file SHA-256 confirmation, strict source flags and input record count gate. Only sanitized booleans and frame count are produced. A PAL, NewPPU or mismatching-FM2 capture is rejected.
- `tools/verify_stage339_legacy_ppu_source.py`: strict version-pinned Git blob contract for owner-local **v2.6.5** `src/ppu.cpp`; rejects wrong source version, missing or ambiguous core anchors. No automatic patching or changes to upstream code are made.
- `tests/test_stage339_mode_and_source.py`: 16 source-free tests covering successful classic NTSC mode, unsupported PPU mode/TV flags, full-file identity, malformed input, duplicate or missing mode, wrong record counts, and source-contract tampering.
- `docs/stage339_public_aggregate.json`: sanitized original mode gate, with explicit negative evidence flags for the still-missing raster witness.

Owner-local command after recovering the verified original source FM2:

```sh
python tools/audit_private_stage339_core_mode.py \
  --movie /private/taotao-viceprojectdoom.fm2 \
  --source-sha256 "$OWNER_PRIVATE_FM2_SHA256" \
  --expected-frames 43652 \
  --output /private/stage339-mode-check.json
```

Before instrumenting an exact FCEUX 2.6.5 source tree:

```sh
python tools/verify_stage339_legacy_ppu_source.py \
  --ppu-source /private/fceux-2.6.5/src/ppu.cpp
```

This verifies source identity and **does not compile or instrument** the emulator.

## Stage 340 legacy witness work specification

Develop opt-in, restricted instrumentation against the original **legacy** PPU core, not NewPPU. Capture the actual source `RefreshAddr`/`TempAddr` changes at classic `Fixit1`, `Fixit2`, CPU `$2006` assignment, and rendering line-boundary/update points, while retaining the owner's exact FM2 core selection and read-only replay. Anchor each emitted event to a proven game frame and CPU cycle or a separately validated raster phase; treat `g_rasterpos` as the classic renderer's coarse pixel position, **not** as an independent hardware PPU dot. Explicitly capture whether a line-pixel observation was renderer-side or a CPU-side update. Bind the original ROM/FM2, executable/source revision and output file identities into an owner-private SHA-256 manifest. Validate readback from Google Drive before claiming a witness is backed up.

An accurate per-dot witness **has not yet been captured**. Existing CPU events and a model cannot reconstruct unknown within-CPU-cycle PPU timing. Do not assert effective raster scroll, camera speed, road geometry or collision until direct source evidence and independent cross-checks exist.
