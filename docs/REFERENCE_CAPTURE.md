# Runtime NES first-stage snapshot capture

This capture workflow supplies the missing **live** evidence. The previous
static reverse engineering identifies CHR sources and PPU command formats,
but cannot recover all colors, nametables or active CHR patterns during gameplay.

## Steps (FCEUX desktop emulator)

1. Open your own Vice: Project Doom ROM in FCEUX.
2. Create a writable directory in the project under ignored private/ and
   set OUTPUT_DIRECTORY at the top of tools/capture_fceux_ppu.lua to it.
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
- frame_NNNNNN.meta.txt — observed PPUCTRL, MMC3 CHR bank writes, frame number
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
