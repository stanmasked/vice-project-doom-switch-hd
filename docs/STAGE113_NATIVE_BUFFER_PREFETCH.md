# Stage113 — native BGData buffered fetch-to-draw witness

Stage112's four synthetic MMC3 programs (0, 4, 8 and 12 CPU NOPs)
showed a monotonic horizontal CHR transition with actual FCEUX XBuf pixels.
Stage113 now observes the specific BGData records rather than assuming
the bank switch immediately alters the next visible tile.

The private patch records source tick and slot index immediately before
and after bgdata.main[xt + 2].Read(). At first-pixel rendering of a tile
indexed by bgtile, it compares the record's two buffered pattern-plane
bytes with the bytes actually consumed by the pixel renderer. Only tiles
whose index and source scanline match are counted, so the carried-over
two records at line boundaries cannot be misattributed.

After the CPU writes to MMC3 $8001, old-buffered tiles are classified
by whether their Record.Read operation began before or after the write;
new-buffered tiles must have been read after the write. FCEUX internal
source-tick differences between end of Read and first tile pixel are
recorded as a bounded min/max, **not** physical NES dots/cycles.
Each run must independently match 128 old and 128 new buffered tiles,
agree with Stage111 on the old-tile count and first new tile, and include
Stage110 pixel-frame proof from the same native process. All four phase
runs and fixed-bank/disabled-probe controls are run under private Xvfb.

This establishes evidence solely for generated, controlled mapper-4 ROMs
and pinned FCEUX internals. It does not reconstruct original-game art,
levels, sprites, CHR banks, or prove hardware-exact timing.
