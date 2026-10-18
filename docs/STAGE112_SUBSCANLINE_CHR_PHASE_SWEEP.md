# Stage112 — controlled subscanline CHR bank-switch phase sweep

Stage111 confirmed an original synthetic mapper-4 ROM switches background
CHR bank during an FCEUX frame and observed the actual **buffered tile**
transition at source scanline 104, with three prefetched old-bank tiles.

Stage112 extends the original Stage110 ROM builder with a separately validated
`phase_nops` parameter: 0, 4, 8, or 12 6502 NOP instructions before the
second $8001 write. Each NOP takes two 6502 cycles, but the experiment
does not assume this corresponds to an exact physical NES dot count.
The rest of the program and both 16 KiB CHR blocks are identical.

Four independent pinned native FCEUX processes each have to generate both
the Stage111 buffered tile witness and the Stage110 final-XBuf witness in
the same process. The strict sweep verifier requires all four source-bank
writes to occur on the same observed FCEUX scanline, with monotonically
later rendered tile columns and first new-bank tile columns. It limits
the prefetch difference to six tiles. Fixed-bank and disabled-hook
negative controls are run separately. All ROMs are private CI temporary
files; none of their bytes, sprites, tile data, or original game assets
are committed.

Results concern synthetic MMC3 and pinned FCEUX timing only, not original
Vice: Project Doom mid-raster behavior, hardware PPU cycle accuracy, or
the future Switch renderer.
