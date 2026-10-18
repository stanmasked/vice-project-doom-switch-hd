# Stage 78 — complete CPU PPU register mirror observation

## Hardware and provenance

The CPU-visible NES PPU registers $2000-$2007 are mirrored every eight
bytes across **$2000-$3FFF**. For example, $200D aliases PPUSCROLL
($2005), $3456 aliases PPUADDR ($2006), and $3FFA aliases PPUSTATUS
($2002). PPUSTATUS reads reset the shared $2005/$2006 write toggle.

References:
- https://www.nesdev.org/wiki/PPU_registers
- https://fceux.com/web/help/LuaFunctionsList.html

The earlier capture hooked only canonical PPU register addresses. This
could silently omit CPU writes/read side effects through mirrored
addresses and distort the reconstructed scroll latch.

## Collector changes

`tools/capture_fceux_ppu.lua` now registers:

```lua
memory.registerwrite(0x2000, 0x2000, on_write)
memory.registerread(0x2000, 0x2000, on_status_read)
memory.registerwrite(0x8000, 0x8000, on_write)
```

The actual CPU address is preserved in the private `mmc3_video_writes.tsv`
and optional `mmc3_ppu_cycles.tsv`. The PPU port is identified by
`(cpu_address - 0x2000) % 8` for accesses in $2000-$3FFF.

The PPU write handler records ports $2000, $2001, $2005, $2006 and
$2007, through any mirror; writes to read-only PPUSTATUS ($2002
mirrors) are *not* misidentified as PPUSTATUS reads. The read
handler observes the entire register window but records only $2002
mirrors, as status-read events with a placeholder value 00.
That placeholder **is not the actual PPUSTATUS bus byte**; FCEUX
registerread supplies an uninformative zero sentinel.

These broad callback hooks can be expensive in FCEUX. The capture
limits, per-frame flushing and dropped-event reporting remain in place.
Callback errors mark captures incomplete.

Completed per-frame metadata now declares:

```text
ppu_register_write_coverage=full_2000_3fff_mod8
ppu_status_read_coverage=full_2000_3fff_mod8
```

The existing MMC3 full-coverage and callback-error fields remain.

## Analysis and compatibility

- `tools/analyze_ppu_scroll_log.py` normalizes PPU addresses before
  reconstructing the observed scroll latch, nametable and $2006 effects.
- `tools/analyze_ppu_cycle_trace.py` accepts PPUSTATUS read markers
  at any $2002 mirror, requires placeholder 00 for a read marker,
  and counts scroll writes through $2005 mirrors.
- `tools/analyze_mmc3_frame_log.py` counts PPU port writes through
  their mirrors but does not infer raster timing.
- Both cycle and optional scroll metadata checks reject older captures
  lacking proof of PPU mirror-hook registration.

The three-column frame log has no event-kind field, so its PPUSTATUS
read markers are distinguished by their (mirrored) $2002 address.
The CPU-cycle log retains explicit R/W kinds. The collector never
inserts read-only $2002 writes as events, avoiding false latch resets.

## ROM-free tests

Existing synthetic tests for the collector, metadata invalidation,
frame MMC3 analysis, scroll latch analysis and CPU-cycle trace have
been updated. They cover $2008/$3FF9/$200D/$3456/$200F, mirrored
$3FFA reads, an unrelated PPU register read, invalid callback
signatures and rejection of legacy metadata. The collector test now
enables a synthetic debugger cycle counter and asserts the
mirrored status event is recorded as kind R.

These changes are part of research branch
`research/stage39-video-trace-alignment` in draft PR #3.
They **do not** reconstruct effective per-scanline PPU state,
the game's stage geometry, or real video evidence. Original ROM
and game assets are not committed. CI success is not established
until jobs actually execute on a GitHub runner.
