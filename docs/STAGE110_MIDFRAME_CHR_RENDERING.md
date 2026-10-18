# Stage110 — controlled mid-frame CHR bank transition

The earlier native stages confirmed the independent operations of selecting
MMC3 CHR, reading background pattern bytes, rendering final framebuffer pixels,
and ordering those synthetic events by internal source ticks.

Stage110 uses a **new, fully synthetic mapper-4 ROM**. Its CPU configures
palette/background and MMC3 command 2, selects blank CHR bank 0, polls
the VBlank bit via BIT $2002, executes a bounded nested 6502 delay, then
writes bank 1 to $8001 while background rendering is active. A second ROM
has identical CHR data and CPU code except the final bank choice stays 0.

A private, opt-in native FCEUX build samples *actual final XBuf bytes* and
the background pixel pattern after the original PPU renderer writes them.
It keeps only 2,048 earliest pre-switch and 2,048 post-switch samples
strictly from the same source PPU scanline traversal. The MMC3 hook records
the real second $8001 write; post-switch sampling begins four scanlines
later so previously prefetched tile patterns cannot be misclassified.
The witness requires an active-rendering switch (source scanline 40-210),
both 2,048-sample groups to match their intended background patterns and
their final-framebuffer FNV-1a digests to differ. The aggregate reports a
synthetic-only line; it never exports a screenshot, raw ROM, CHR contents or
any original game pixel.

The fixed-bank ROM and an explicitly disabled observer must *not* generate
a positive proof. The native result, not the unit-test fixture, decides
whether the switch truly occurs within one FCEUX-rendered frame.

Source scanlines belong to this pinned FCEUX version; the experiment does
not certify physical NES timing, Vice: Project Doom level geometry, or
real-game mid-frame bank switching.
