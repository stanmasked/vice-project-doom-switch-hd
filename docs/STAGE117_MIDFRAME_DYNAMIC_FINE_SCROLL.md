# Stage117 — native mid-raster $2005 fine horizontal scroll write

Stage116 verified four *pre-render* fixed fine-X offsets; Stage117 checks
a different effect. A generated synthetic MMC3 ROM begins at fine X=0,
switches CHR bank at the previous stage's controlled mid-frame position
and then writes a new nonzero `$2005` horizontal offset **while rendering**.
A second `$2005` zero write resets the X/Y toggle without changing fine X.

The source-guarded private patch observes the real `B2005` assignment
`ppur.fh = V & 7` and the existing final newppu XBuf/background pixel
hook. It requires that the CPU write occurs in a visible source scanline
after the mapper write. For 64 subsequent pixels on the very same line
and 16 pixels on the following line, it checks observed fine X, source
tile index `(rasterpos + fine) >> 3`, bit position, both buffered CHR
pattern-plane bytes and the lower background pixel bits. It rejects
lost/duplicate writes, out-of-order source events or inconsistent banks.

Four generated Mapper-4 ROMs target fine scroll offsets 1, 3, 5 and 7.
Each has a same-process Stage110 native final-framebuffer witness. A
fixed-bank ROM and a probe-disabled ROM must remain negative controls.
All ROMs are generated only in private CI temporary directories.

**Scope:** a pinned FCEUX internal renderer experiment, not proof of
cycle-exact hardware scrolling, of original Vice: Project Doom game
raster behavior, or of a Nintendo Switch HD renderer. Later research
must inspect dynamic coarse scroll, Y scroll and original-game evidence.
