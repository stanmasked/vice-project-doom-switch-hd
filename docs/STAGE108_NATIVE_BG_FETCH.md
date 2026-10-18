# Stage108 — PPU background CHR fetches linked to final pixels

Stage107 (native FCEUX pass) confirmed two synthetic MMC3 bank selections
produce different *final framebuffer* bytes. Stage108 adds a separate
observer at FCEUX newppu's two background pattern fetch assignments:
`pt[0] = CALL_PPUREAD(RefreshAddr)` and
`pt[1] = CALL_PPUREAD(RefreshAddr)`. The hook is compiled and runtime
enabled explicitly. It accepts only generated synthetic mapper-4 ROMs.

For 8192 paired reads per ROM, the native observer counts all-zero,
all-FF and unexpected CHR source bytes. It checks normal low/high
background plane alternation, high-plane address +8, and the
background pattern-table address range. Read values and addresses are
not logged: only bounded, aggregate counts and a fail-closed marker.

Two independent native FCEUX processes select CHR bank 0 and bank 1;
their corresponding native Stage107 pixel markers are observed in the
**same processes**, not from unrelated captures. Positive acceptance
requires bank-appropriate fetch byte counts *and* different final
framebuffer checksums; a third opt-out run rejects either marker.

This is still evidence for the synthetic ROM and native emulator only.
It does not authenticate Vice: Project Doom CHR pages, real-game raster
timing, stage-one art, scroll, sprites, or Nintendo Switch rendering.
