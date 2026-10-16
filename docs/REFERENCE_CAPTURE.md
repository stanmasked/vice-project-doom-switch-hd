# Runtime NES first-stage snapshot capture

This capture workflow supplies the missing **live** evidence. The previous
static reverse engineering identifies CHR sources and PPU command formats,
but cannot recover all colors, nametables or active CHR patterns during gameplay.

## Steps (FCEUX desktop emulator)

1. Open your own Vice: Project Doom ROM in FCEUX.
2. Create a writable directory in the project under ignored private/ and
   set `VPD_CAPTURE_DIRECTORY` before loading tools/capture_fceux_ppu.lua (or\n   change its private output directory default).
3. Launch that script with the FCEUX Lua Script Window; play into the first
   level. By default, a PPU/RAM snapshot is written every 120 frames,
   for up to 24 captures.
4. Inspect the outputs locally:
   
   python3 tools/render_ppu_snapshot.py private/frame_000240 --out private/preview --pattern-base auto

5. The tool produces one static PNG per nametable and (if PPUCTRL was not
   observed) **both** plausible 4KiB background pattern-table interpretations.
   A JSON report summarizes the captured palette entries and tile occupancy.

FCEUX APIs used: emu.registerafter, emu.framecount, memory.registerwrite,
memory.readbyterange, ppu.readbyterange, and rom.gethash. See
https://fceux.com/web/help/LuaFunctionsList.html for the documented API.
The Lua capture has **not** yet been executed in FCEUX by CI: manual runtime
validation is still required.

## Files (private only)

- frame_NNNNNN.ppu.bin — 16KiB view of current PPU address space
- frame_NNNNNN.ram.bin — 2KiB CPU work RAM (includes $0600 queue and $0700 sprite DMA)
- frame_NNNNNN.meta.txt — observed PPUCTRL, MMC3 CHR bank writes, frame number\n  and a **register_log_complete** indicator; reject incomplete logging for timing analysis
- mmc3_video_writes.tsv — register writes including $8000/$8001 and PPU ports

Do not add captured graphics, RAM, palette values or other original-game
data to Git. No commercial game files are included in CI.

## Interpretation warning

Output images are background reconstructions from *one snapshot*, not full
NES video frames. Vice uses MMC3 IRQ processing and can swap CHR banks within
the same frame. PPU scrolling, mirrored nametables, 8x8/8x16 sprites, sprite
priority, color emphasis, and analog NTSC characteristics are not emulated.
NES RGB reference palette colors are approximate.

## Next

With the first playable scene's snapshots and register log, identify actual
background CHR patterns, palette data and visible nametable sections, then
reproduce the scene as independent native geometry and new HD artwork.


## Comparing adjacent captures

For two captured frames, run the ROM-free comparison tool:

    python3 tools/compare_ppu_captures.py private/frame_000240 private/frame_000360 --out private/frame_diff.json

It reports changed CHR 1KiB pattern pages, nametable tile bounding boxes,
attribute byte differences, palette entries, CHR register RAM values,
the number of changed PPU queue bytes, and 4-byte OAM-source slots in RAM $0700.
The report is a **summary**, not a reconstruction of scanline IRQ state.

## v2 capture compatibility and bounded write logging

FCEUX **2.3+** documents the Lua `ppu.readbyterange` function. The script
now checks the returned PPU/RAM lengths, writes snapshots as binary,
flushes register events after every frame, and records overflow explicitly.
The register log is capped at **12,000 writes/frame** and
**250,000 writes/session**. Once any records are dropped, captures say
`register_log_complete=no` and include `dropped_register_writes`.
Do **not** infer accurate frame timing from an incomplete log.

GitHub CI exercises the **actual Lua script** with a fake FCEUX API,
writing two fabricated 16KiB/2KiB captures and deliberately overflowing
one frame's event log. This is **not** a verified real FCEUX game capture.

## Static OAM sprite compositing

Given one complete captured PPU/RAM snapshot:

    python3 tools/render_oam_sprites.py private/frame_000240 --out private/preview/oam.png --scale 3

The renderer samples the game's observed PPUCTRL (8x8 versus 8x16 sprite
size; sprite pattern selection), PPUMASK, the sprite DMA source page at
CPU RAM `$0700`, and NES sprite palettes. It handles 8x8/8x16 sprites,
horizontal/vertical flip, transparency, source OAM ordering, left-edge
clipping and basic sprite-behind-background priority.

If PPUCTRL is missing, supply explicit
`--bg-pattern-base 0x0000 --sprite-pattern-base 0x1000 --sprite-height 8`
settings only if measured from the actual game. Otherwise the tool refuses
to guess.

**Important:** This is one *static* OAM overlay, not the complete live
original frame; a 6502/MMC3 game can alter banks and scrolling within
the same frame. True HD art must be newly authored.


## Stage 19: actual rendered-frame reference (capture format v3)

The FCEUX Lua capture can now record the **image the emulator actually rendered**, independently from its static PPU memory. Per sampled frame it writes two additional *private* binary files:

- frame_NNNNNN.screen.rgb.bin — 256x240x3 RGB bytes, top to bottom.
- frame_NNNNNN.screen.pal.bin — 256x240 NES palette indices (0-63); 254 means the color index was unavailable.

Both come from the documented emu.getscreenpixel(x,y,true), queried in the same emu.registerafter callback as the PPU/RAM capture. Metadata records format=fceux_ppu_snapshot_v3, screen_reference=yes, screen_size=256x240, and invalid_screen_palette_values. Sampling 61,440 screen pixels per saved frame can cost time. To opt out, set the Lua global VPD_CAPTURE_SCREEN=false before executing the script (default: enabled).

Compare to a static background from an owned-ROM capture:

    python3 tools/compare_rendered_frame.py private/frame_000240 --mode background --nametable 0 --out private/reference_comparison

Or include static OAM sprite compositing:

    python3 tools/compare_rendered_frame.py private/frame_000240 --mode sprites --nametable 0 --out private/reference_comparison

If PPUCTRL is unknown, explicit pattern-table selection is required for backgrounds; the sprite comparison needs observed PPUCTRL. The analyzer compares NES palette **indices**, rather than approximate RGB colors, to avoid mistaking an emulator's color-profile choice for a tile-layout error. It emits a mismatch fraction, the worst 12 scanlines, a color-coded mismatch heatmap and the observed FCEUX RGB frame.

Differences may originate in scroll position, scanline IRQ CHR changes, OAM evaluation, grayscale/color emphasis, or PPU timing—not only extraction errors. A close match does NOT prove original game logic or video behavior has been recovered.

Actual screen frames, PNGs and reports produced from the original ROM are private and never belong in GitHub or CI artifacts. The Lua mock verifies the file contract but does not represent an actual FCEUX gameplay capture.

Reference: https://fceux.com/web/help/LuaFunctionsList.html

## Stage 32: collect enough overlapping first-stage observations

A new [tile-mosaic stitcher](STAGE_MAP_EVIDENCE.md) can correlate multiple
private FCEUX PPU snapshots **only with externally verified** camera
and scroll positions. It preserves disagreements instead of converting
tile observations into guessed collision geometry.

Set `VPD_CAPTURE_INTERVAL` and `VPD_CAPTURE_LIMIT` globals before
running the Lua script to acquire more overlapping frames. Defaults
remain 120 and 24; use e.g. 8 and 96 for dense user-controlled
sampling while first entering the playable stage. Set
`VPD_CAPTURE_SCREEN=false` to skip expensive screenshot collection
if only PPU memory and register logs are required.

See [STAGE_MAP_EVIDENCE.md](STAGE_MAP_EVIDENCE.md) for the strict
manifest, camera measurement requirements, sample commands and
limitations. No real first-stage camera values or collision map have
been recovered by these tests.

## Stage 33: validated PPU scroll-source instructions

Local static analysis of the owned original ROM found an exact
fixed-bank $E8DE routine that reads RAM $0B then writes PPU $2005,
reads RAM $0D and writes PPU $2005 again. $0C supplies the low bit
of the PPUCTRL calculation. This is a **verified scroll-register
source**, not independently confirmed world-camera data.

The local FCEUX Lua metadata now includes
`scroll_emitter_ram_0b`, `scroll_emitter_ram_0c`, and
`scroll_emitter_ram_0d`. These are snapshot-time RAM values.
The script marks their provenance as static-only; only CPU-cycle
runtime verification can prove the emitter executed. See
[SCROLL_SOURCE_AUDIT.md](SCROLL_SOURCE_AUDIT.md).

## Stage 35: capture candidate descriptor pointer provenance

The ROM-local audit identifies an exact bank-12 setup of zero-page
pointer `$AA/$AB` from RAM `$92`, with nearby reads into
`$A8/$A9`. A bank-14 decoder reads `($AA),Y`. **Whether these
routines share that pointer at first-stage runtime remains unverified.**

The FCEUX snapshot metadata records $92/$AA/$AB/$A8/$A9 as
`stage35_candidate_...` fields, explicitly labelled static-only.
See [INDIRECT_POINTER_TRACE.md](INDIRECT_POINTER_TRACE.md) for
the three exact opcode anchors, MMC3 mode-0 mapping requirement and
the carry-handling edge case at hypothetical index 86.
