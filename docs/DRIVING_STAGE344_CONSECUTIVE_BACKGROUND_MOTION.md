# Stage 344 — authenticated adjacent-frame background displacement

## Scope and source identity

Stage 343 established native 256×240 FCEUX `gui.gdscreenshot(false)` RGB and the same-session Stage335/Stage341 CPU/PPU event baselines. Stage 344 replays the **original, owner-private ROM and FM2 read-only** on the same FCEUX 2.6.5 instrumented **classic PPU** (`NewPPU 0`), this time capturing **all 25 consecutive frames 420–444** at the Stage335 `emu.registerafter` frame-end callback. Three frames also include full 256×240 indexed-palette planes. There is no display rescaling, bilinear interpolation, unknown pixel buffer, emulator core switch, or synthetic game frame in the evidence.

The new private session's full Stage335 CPU and Stage341 native classic PPU TSV files are byte-identical to the previously sealed witnesses (full SHA-256 compared locally). Its 261-frame `COMPLETE.txt` confirms read-only FM2 and original ROM identity. A fresh owner-private manifest binds **every** GD screenshot, index plane, palette sample and raw CPU/native TSV to its own SHA-256. The manifest and raw data must remain private, never in the public GitHub repository.

## What was measured

The owner-local auditor `tools/audit_private_stage344_motion.py` checks strict GD 256×240 dimensions, samples and index files, private hashes, original frame continuity, both complete CPU/PPU frame-anchor sequences, 150 independent sampled RGB/palette probes, and the 3 indexed-palette files. For each of the 24 adjacent pairs it compares exact RGB pixels under candidate vertical shifts −4…+4 in *four separate non-sprite/non-HUD texture bands*. Each band must have a uniquely discriminating minimum with a quality threshold. All four bands must choose the same displacement; flat, ambiguous, contradictory, tampered or missing original evidence makes the run fail closed.

These research image masks were selected by private visual inspection of original game screens, not inferred from a level layout:

- Left environment: x = 0…51, y = 20…174
- Right environment: x = 195…254, y = 20…174
- Left visible road-marking strip: x = 93…98, y = 20…174
- Right visible road-marking strip: x = 157…162, y = 20…174

The central vehicle, blinking sprite and HUD region are excluded. Regions are candidate observed texture areas only, **not** a formal road-width definition.

**Original-source result:** Each of 24 adjacent pairs has identical decisions in all four independently assessed bands. 11 pairs match zero vertical displacement (frames 420→421 through 430→431). 13 pairs match a **+1-pixel displacement in image coordinates** (431→432 through 443→444), meaning background features move down one display pixel from one frame to the next in the selected regions. The largest best-shift mismatch fraction across the 96 bands is 0.1505; source pixel palettes or background tiles can change without justifying a different displacement. The source result is a *bounded 25-frame display observation*, not an inferred general driving rate.

This result must **not** be described as independent physical PPU-dot phase, mid-scanline road scroll, reconstructed road perspective, car velocity, camera speed throughout the game or collision physics. Road geometry and playable driving dynamics have **not** been updated on the basis of these captures.

## Public-safe changes

- `tools/audit_private_stage344_motion.py`: strict source-file/manifest and adjacent masked RGB-motion validator that outputs only counts and boolean statements.
- `tests/test_stage344_background_motion.py`: 15 synthetic-only regression/negative cases, including stationary/one-pixel motion, independent band disagreement, sprite/HUD changes, flat texture, source tampering, invalid GD, wrong palette samples, missing/duplicated frame witnesses and wrong film source identity.
- `docs/stage344_public_aggregate.json`: non-sensitive aggregate with the observed displacement **counts** but no source RGB, palette indices, car imagery, ROM/FM2 bytes, original SHA-256, CPU cycles or raw addresses.

## Reproduction in the owner-private workspace

Generate a private Stage343-style Lua extension of the **exact Stage335 Lua source** (do not check its outputs into Git) with `--frames 420,421,...,444` and `--palette-frames 420,432,444` using `tools/generate_private_stage343_rgb_capture.py`. Use the pre-verified Stage341 instrumented FCEUX binary and the Stage341 private capture runner, with `LD_LIBRARY_PATH` including the privately extracted `liblua5.1.so.0` directory if absent from the host. Recheck the original ROM/FM2 hashes. The only accepted output is a newly created directory, never an existing capture path.

Create an owner-private SHA manifest in format `vpd_stage344_original_consecutive_rgb_private_manifest_v1` with exactly the selected frames, sealed CPU/PPU checksums, `newppu: 0`, `original_readonly: true`, and per-file SHA-256. Run:

```
python tools/audit_private_stage344_motion.py --root "$OWNER_PRIVATE_STAGE344_ROOT" \
  --manifest "$OWNER_PRIVATE_STAGE344_MANIFEST" \
  --sealed-cpu-sha256 "$OWNER_PINNED_STAGE335_SHA256" \
  --sealed-native-sha256 "$OWNER_PINNED_STAGE341_SHA256" \
  --output "$OWNER_PRIVATE_STAGE344_REPORT"
python -m unittest discover -s tests -p 'test_stage344_*.py' -v
```

Backup the raw pixel/witness archive, manifest and report to the existing **owner-private** Drive project archive. Re-download and independently check byte size, ZIP integrity and SHA-256 before claiming durable storage. Maintain Draft PR #99 and preserve unchanged main.

## Next

Stage 345: investigate the true rendering start and finer road pixel displacement across additional original consecutive windows, and independently compare feature movement to the classic PPU scroll registers and RAM `$0D` *without assuming they are the same physical quantity*. Require a new authenticated source window before inferring a more general motion law. No original source data in public GitHub Actions.

## Stage 345 prerequisite — independent sealed-source identity gate

The initial Stage344 auditor authenticated every file against the capture session manifest, but a mistakenly replaced CPU/PPU trace **and the manifest rewritten together** would remain self-consistent. The auditor now also **requires independent Stage335 and Stage341 SHA-256 pins**, supplied from prior owner-private sealed records via CLI. A SHA copied from the new Stage344 manifest is **not** an independent seal. The two external values are compared to capture hashes **before** pixel analysis; malformed, missing, or mismatched pins fail closed.

The ROM-free synthetic suite adds two regressions for a jointly rewritten native trace/manifest and an invalid pin. This is a *reproducibility and provenance correction*, not new original-game capture. It does not extend the measured frame window, establish an exact NES PPU dot, or prove camera/vehicle mechanics. New source conclusions require a fresh owner-private authenticated execution and Drive-verified archive.
