# Stage 20 — scrolling backgrounds and conservative PPU latch trace

## NES 2x2 logical nametable scrolling

The diagnostic frame comparator now models the **common NES scrolling
configuration** with four logical nametables (256×240 each). The top-left
nametable index is supplied explicitly (or derived separately from a
verified PPUCTRL write), with normal PPUSCROLL offsets:

- Horizontal X: 0–255 pixels (may cross into the adjacent logical table).
- Vertical Y: 0–239 pixels (may cross into the table below).
- Pixel coordinates wrap across the four logical nametables (512×480).
- For each sampled pixel, tile and palette-attribute lookup is performed
  in the *selected* logical nametable, not a single original table.
- Sprite-behind-background priority tests the **scrolled** background's
  actual 2bpp value; 0 is transparent for this purpose.

The input PPU snapshot already contains the mapper-resolved address-space
view. This code does not attempt to guess cartridge mirroring from the
original ROM, or emulate CIRAM or CHR bank switching.

The algorithm is intentionally **not** a full PPU implementation. It rejects
vertical values 240–255 because the NES can then render attribute-table
bytes as tiles (requiring a more detailed loopy-v model). Split-screen
scrolling, scanline IRQ effects, sprite-0 timing, NTSC filtering and changing
CHR banks within a frame remain outside this diagnostic.

## Comparing an observed frame using measured scroll

~~~sh
python3 tools/compare_rendered_frame.py private/frame_000240 \
  --nametable 0 --pattern-base 0x0000 \
  --scroll-x 245 --scroll-y 16 \
  --mode sprites --out private/scrolled_frame_report
~~~

The example numbers above are **invented**, not original game values.
Use actual measured offsets for evidence-backed comparisons. Omitting
either offset means it defaults to zero and is recorded as
`scroll_provenance=partially_or_fully_assumed_zero`. Even explicit offsets
must not be treated as display-effective merely because they appear in a
frame-number-only CPU write log.

## Identifying paired PPUSCROLL writes

The Lua capture now records a marker `2002 00` on a CPU **read** of
PPUSTATUS, in addition to the usual write events. The existing
`mmc3_video_writes.tsv` name is retained for backward compatibility,
but the file now contains this one specifically documented *read* marker.
Its header remains `frame address value`; marker value 00 is synthetic
and is **not** the actual PPUSTATUS register value.

This is required because PPU registers $2005 (PPUSCROLL) and $2006
(PPUADDR) share a first/second-write toggle. Reading $2002 resets
that toggle to its first-write state. If a log began after power-on and
has not observed a $2002 read, the starting toggle remains **unknown**.
Interleaved $2006 writes invalidate any pending $2005 pair rather than
inventing a complete scroll measurement.

~~~sh
python3 tools/analyze_ppu_scroll_log.py private/mmc3_video_writes.tsv \
  --metadata private/frame_000240.meta.txt \
  --out private/ppu_scroll_summary.json
~~~

The summary contains last observed complete (X,Y) pairs, originating
frames, and whether Y falls inside the normal 0–239 range. Supplying
metadata causes the analyzer to refuse traces with incomplete or unknown
`register_log_complete` flags. A frame-only log is **not** adequate to
determine exactly when a changed scroll affected the visible scanline.

## Validation

Six ROM-free tests exercise pixel/tile boundaries, two-axis nametable
wrapping, sub-tile offsets, sprite priority over a scrolled background,
pixel-index comparison and unsupported Y values. Five more invented-event
tests check $2002 latch reset, $2006 interference, incomplete state, and
out-of-order timestamps. The FCEUX Lua mock additionally verifies the
read-event hook. No commercial ROM or stage art is committed to GitHub.

References: [NESdev PPU scrolling](https://www.nesdev.org/wiki/PPU_scrolling)
and [PPU programmer reference](https://www.nesdev.org/wiki/PPU_programmer_reference).

## Remaining blockers

On 21 October 2026, real FCEUX 2.6.5 playback of the owner's USA ROM+FM2
provided original Stage 1-1 RGB/palette screenshots and **observed CPU
$2005/$2000/$2006 write events** for frames 600–920, plus sampled RAM $0B/$0C/$0D.
The private CPU trace contains exactly four $2005 writes on each of those
321 frames. These are verified CPU-write observations, **not** full PPU
memory snapshots or display-effective scroll. The running FCEUX Lua API lacks
`memory.registerread`, so no $2002 latch-reset witness was obtainable that
way; the capture code records this limitation rather than inventing events.
See [original Stage 1-1 timing/road evidence](ORIGINAL_STAGE_TRANSITION_CONTRACT.md).

Still unresolved: complete original PPU nametable/CHR snapshots, subframe
raster and IRQ effects, exact scanline-effective scroll, first-stage collision
geometry, and separate original title-scene provenance. The native Switch
prototype remains distinct from these original-game observations.
