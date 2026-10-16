# Stage 25 — SD-card VPAT override and safe reload

The native Nintendo Switch ROM-free diagnostic now reads an optional
developer-made sprite atlas from SD **without rebuilding the NRO**.
This supports iterating on independently authored artwork. The build remains
a diagnostic, **not** the original Vice: Project Doom gameplay or HD art.

## Install

Place the optional texture at this exact path:

    sdmc:/switch/vice_project_doom/hero.vpat

Recommended SD-card layout:

    switch/
      vice_project_doom/
        vpd_native_scene.nro
        hero.vpat

The NRO comes from GitHub Actions artifact vpd-native-raster-scene.
No original NES ROM, proprietary tiles or art assets are required.

If a working SD mount and valid external atlas are available at startup,
the diagnostic uses the external art. Otherwise the embedded independent
red character is retained. The SD file is never modified by the program.

## Controls

- X: reload and validate the current SD texture file synchronously.
- Y: reset to the embedded red sprite; release external texture memory.
- D-pad / left stick: move; A/B: jump; Plus: quit.

HUD feedback: ART: SD OVERRIDE, ART: EMBEDDED, or RELOAD FAILED.
A failed manual reload keeps the last known valid sprite. Y clears the
error. There is no background scanning and no network download.

## Safety, compatibility and limitations

The portable AssetSource component owns all accepted external byte buffers,
protecting the SpriteAtlas non-owning pointer from stale memory.

A reload is committed *only after* validating:

1. File opens and is bounded by 4 MiB pixel payload + 22-byte header.
2. All bytes were read without an I/O failure or concurrent file growth.
3. VPAT v1 magic, version, dimensions, flags and payload length are valid.
4. CRC32 of RGBA8888 payload matches the expected value.
5. Atlas has exactly four frames, matching the compiled animation manifest.

CRC32 detects accidental corruption; it is not a cryptographic signature.
If validation fails, no partial replacement occurs. The embedded fallback
remains available for the lifetime of the application.

The current manifest still defines idle, two running poses and an airborne
pose, using independently authored placeholder timing. A new atlas can have
larger pixel dimensions (within VPAT v1 limits), but must still contain
four cells. The hardcoded sprite draw scale and placement may require
changes for real high-resolution artwork.

## Author a replacement atlas

For a 96x32 RGBA PNG sheet with four 24x32 cells, execute:

    python3 tools/pack_vpat.py private/hero.png \
      --frame-width 24 --frame-height 32 --frames 4 \
      --binary private/hero.vpat

Then copy private/hero.vpat to the SD path above and press X in the running
diagnostic. Different artwork can be loaded without C++ recompilation.

The separately downloadable stage-25 test ZIP includes a *blue*
synthetic sprite, editable PNG and preview. It does not contain the ROM or
any recovered original assets.

## Verification

Host regression tests cover valid replacement, changed rendered output,
broken CRC, truncated files, oversized inputs, wrong frame count, missing
files, preservation of the last valid resource and restoration of fallback.
Both Linux C++ tests and Switch devkitPro NRO builds are run in the native
graphics GitHub Actions workflow.

**No physical Switch execution is claimed.** SD permissions, latency,
frame pacing and performance remain unmeasured on hardware. The first
authentic Vice: Project Doom level remains unextracted and unvalidated.

See ASSET_PIPELINE.md and ANIMATION_CONTROLLER.md for atlas encoding,
frame selection, and animation state design.

## Stage 26: optional external animation timings

The stage-25 `hero.vpat` location is unchanged. For a paired external
animation schedule, add a binary `hero.vanm` in the **same SD directory**.
This controls the frame indices and durations for idle, run, rise and fall.

**X** validates both files and applies them together. A damaged/incompatible
VANM blocks the entire update and preserves the previous valid resources.
**Y** returns to embedded pixels **and** embedded timing. If VANM is missing,
an external VPAT alone continues to work with the embedded clip schedule
(legacy compatibility). The fixed total of four clip states is unchanged.

Use [EXTERNAL_ANIMATION.md](EXTERNAL_ANIMATION.md) for the VANM binary
layout, Python JSON packer, controls, bounds and known limitations.
