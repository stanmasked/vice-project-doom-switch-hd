# Stage111: synthetic buffered background tile transition

Stage110 established native FCEUX MMC3 bank switching inside one rendered
frame. Stage111 links this change to bytes consumed by individual background
tiles: the newppu BGData buffered pattern-plane pair at the final XBuf pixel
sink, not merely CHR register writes or earlier pattern fetch callbacks.

An opt-in private FCEUX hook observes the first pixel of each rendered tile.
It requires 128 blank-buffer old-bank tiles, tracks old-bank prefetched tiles
after the write, then requires 128 filled new-bank tiles without regression.
The first new tile must be observed by three source scanlines after the write.
The paired Stage110 witness from the same native process proves distinct
XBuf framebuffer byte hashes for the before/after pixel windows.

All tests use original, generated mapper-4 synthetic ROMs; no original game
ROM bytes, CHR pages, pixel captures, or raw addresses are published.
Negative fixed-bank and disabled-hook runs must never produce a positive
marker. Source scanlines and tile columns are internal emulator positions,
not claims about exact NES hardware raster timing.

This does not reconstruct Vice: Project Doom original map or sprites and
does not validate original-game CHR banking or Switch gameplay.
