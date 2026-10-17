# Stage115 — two-tile background buffer carried across a newppu scanline

FCEUX pinned source executes `bgdata.main[0/1].Read()` at the very
end of one scanline, after sprite fetches. The first two background
tiles at the start of the next scanline are drawn from those already
buffered records. Stage115 instruments **the existing two-iteration loop**
without moving those reads or losing the loop's scoping.

For 16 visible synthetic scanlines (96–111), the native hook compares
both record plane bytes, original source scanline, MMC3-write epoch and
actual XBuf render consumption for both tiles. The stage additionally
requires the synthetic fine horizontal scroll to remain zero. The
switch at source scanline 104 means the first two tiles of that line
still use bank zero, while the first two tiles of line 105 use bank one.
The aggregate must contain exactly 18 blank and 14 filled edge tiles,
with a bounded internal clock gap from read completion to consumption.

Every one of four CPU NOP phase programs (0/4/8/12) must yield the
cross-line aggregate and companion stage111 tile, stage113 prefetch,
stage114 low/high plane and stage110 framebuffer evidence from the
**same real native FCEUX process**. Fixed-bank and observer-disabled
ROM runs are required negative controls. Original generated synthetic
ROM bytes and CHR planes remain private in the GitHub Actions runner.

Crucially: this proves a fixed-scroll internal FCEUX buffering case.
Dynamic `$2005` fine/coarse scroll transitions are not measured here,
nor are original Vice: Project Doom levels, sprites, backgrounds or
hardware-exact NES raster timings. Such cases need later experiments.
