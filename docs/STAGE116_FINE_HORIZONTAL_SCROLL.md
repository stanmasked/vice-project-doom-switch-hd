# Stage116 — native $2005 fine horizontal scroll and prior-row BGData tiles

The pinned FCEUX PPU register write for $2005 updates `ppur.fh = V & 7`
on the first write. At the final framebuffer sink, `bgpos = rasterpos +
ppur.fh`, `bgtile = bgpos >> 3` and `bgpx = bgpos & 7`. Thus nonzero
fine horizontal scroll can make the first eight screen pixels consume
pattern bytes from **both** BGData carry slots 0 and 1, which were read
at the end of the previous scanline.

Stage116 extends only original generated synthetic mapper-4 ROMs with
bounded first and second `$2005` writes before display enabling. The
legacy zero-scroll ROM is unchanged. Four independent pinned native
FCEUX sessions check fine offsets 0, 1, 3 and 7. A separate opt-in
observer sees the real two end-of-line BGData records and validates
every first-screen-tile pixel's source buffer, pattern-plane pair,
actual bgpx and bgtile, MMC3-write epoch and source scanline. It checks
128 pixel-source samples over 16 lines: 72 from old bank and 56
from new bank. Slot-1 consumption should be 0, 16, 48 and 112 pixels.

Each positive run must also contain the Stage110 native XBuf framebuffer
proof from the **same FCEUX process**. The control with a fixed MMC3
bank and the observer-disabled control must not emit a positive marker.
No game ROMs, textures, sprites or screenshots are uploaded to GitHub.

Timing is internal pinned-FCEUX source-tick timing, not guaranteed
NES hardware PPU dot accuracy. These fixed-scroll synthetic samples
do not validate dynamic mid-frame scroll writes or any original
Vice: Project Doom graphics or Nintendo Switch HD renderer.
