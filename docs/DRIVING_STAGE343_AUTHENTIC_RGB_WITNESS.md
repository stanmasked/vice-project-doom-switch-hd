# Stage343 — original FCEUX renderer RGB witness aligned with CPU and PPU

## Provenance and result

The owner's private NTSC `NewPPU 0` original FM2 (43,652 inputs) and original NES ROM were replayed **read-only** in the Stage341 separately built FCEUX v2.6.5 classic PPU binary. An explicitly authenticated source-hash-guarded Lua extension was inserted into the already successful Stage335 capture callback, **after each CPU `frame_end` event** and before the callback advances, ensuring the image sample refers to the same FCEUX core frame. The Lua source extension kept all old CPU callback output intact. The returned CPU trace is **byte identical** to the sealed Stage335 original trace; the concurrent classic internal PPU trace is **byte identical** to the sealed Stage341 native trace. This independently revalidates both prior witnesses in the same actual image-producing replay.

Captures are made with FCEUX `gui.gdscreenshot(false)`, explicitly reading **current XBuf** and **not the backup XBackBuf**. The pinned FCEUX v2.6.5 implementation packs a truecolor GD header (magic 0xFFFE, 256 × 240, 11 header bytes) followed by 256×240 pixels in ARGB byte order. Original resolution and screen pixel order are preserved; no viewport rescaling or interpolation is performed. Six fixed `emu.getscreenpixel(x,y,false)` cross-checks per frame verify raw RGB and actual palette indices against this GD data. For four frames, the Lua additionally reads **all 61,440 palette indices** and asserts RGB equivalence at every pixel during the same frame callback.

The private source capture collected **12 original frames** (380, 387, 388, 389, 392, 396, 397, 400, 420, 480, 560, 640), or **737,280 original RGB pixels**, with 72/72 independent RGB/palette probe matches. Four complete 256×240 indexed-palette planes were captured. Sampled frames 380–400 had a uniform black XBuf; samples 420, 480, 560, 640 have multiple colors. *These are sampled frames, not a complete onset/disappearance map*. A private visual examination of the latter shows game road/vehicle/HUD imagery. The instrumented runtime produced 261 frames of matching CPU and PPU observations as before.

## Implementation and reproducibility

- `tools/generate_private_stage343_rgb_capture.py`: source-hash-guarded, fail-closed generator of an **owner-local** supplemental Lua probe; it does not contain the original ROM, movie, addresses or pixels. Refuses altered callback signatures, ambiguous callbacks, duplicate frames, palettes without RGB frames, or overwrites.
- `tools/audit_private_stage343_rgb_frames.py`: validates native 256×240 GD format and GD alpha, owner-provided source SHA-256 identities, movie/frame markers, sampled frame coverage, individual RGB/palette probes, full indexed-palette frame sizes, and pixel-level frame differences. Emits *only non-identifying aggregates*, no original images or palette values. Explicitly marks unknown per-dot or gameplay semantics.
- `tests/test_stage343_rgb.py`: 12 source-free fabricated-frame regressions, including hostile malformed headers, colors, palette planes, missing markers and mismatching digests.
- `docs/stage343_public_aggregate.json`: source-backed privacy-filtered results without source pixel colors, ROM identifiers, private source hashes or timestamps.

The original full-size GD frames, indexed-palette planes, Lua patch, session logs, same-session raw event traces, original ROM/FM2 hash binding and each file's SHA-256 are stored **only in the owner-private Drive evidence archive**. Raw image data must not be uploaded to public GitHub Actions or this repository.

## Evidence boundary and Stage344

Frame labels are authenticated to the original FM2 and the classic FCEUX CPU/PPU trace, but `gui.gdscreenshot(false)` is an emulator renderer buffer, **not physical NES PPU dot instrumentation**. The captured image confirms what FCEUX actually rendered at these sample frames; it does not by itself identify a precise road/perspective raster strip, deduce within-frame mid-scroll geometry, establish camera speed or collision. The first eight image samples are black, so a visual analysis must focus on independently selected nonblack consecutive frames. Stage344 should collect bounded consecutive road frames (e.g. 420–432), validate their CPU/PPU same-session baseline identically, and develop *region-level* motion estimation with explicit sprite/HUD masking. Do not substitute modeled road positions for source pixels.

Maintain Draft PR #99. Do not merge to main or publish original ROM, FM2, source RGB, screenshots, indexed palette data or raw PPU traces.
