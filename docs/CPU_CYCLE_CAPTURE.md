# CPU-cycle trace for MMC3/PPU (research milestone 21)

The original NES ROM **never enters GitHub**. Capture must be performed locally
in an FCEUX instance already running a user-owned `Vice: Project Doom` ROM.
This workflow increases timestamp resolution but **does not reproduce** the
original game engine, or prove which CHR bank was visible at a particular
scanline.

## What changed

`tools/capture_fceux_ppu.lua` keeps the backwards-compatible
`private/mmc3_video_writes.tsv` (frame / address / value) and, if the
documented `debugger.getcyclescount()` API is available, also writes:

```text
private/mmc3_ppu_cycles.tsv
frame   cpu_cycle   address   value   kind
```

Here `kind=W` is a CPU memory-mapped register write; `kind=R` is
specifically the **PPUSTATUS read** marker at address `$2002` with an
artificial value of `00`. The CPU-cycle clock starts at power-on or the
debugger's last reset and is **not** reset to the start of each NES frame.

New snapshot metadata:

- `format=fceux_ppu_snapshot_v4`
- `cycle_trace_available=yes|no`
- `cycle_trace_counter_epoch=debugger_since_reset`
- `register_log_complete=yes|no`
- `dropped_register_writes=<count>`

The event logger buffers and flushes each frame and retains explicit drop
counts if either the per-frame or session recording limit is reached.
`cycle_trace_available=no` means an FCEUX environment did not expose the
cycle clock; the normal frame-only TSV remains available for older tools.

## Local analysis

After capturing frames, run:

```bash
python3 tools/analyze_ppu_cycle_trace.py private/mmc3_ppu_cycles.tsv \
  --metadata private/frame_000240.meta.txt \
  --out private/mmc3_cycle_report.json
```

The tool refuses incomplete register captures or missing CPU-cycle clock
metadata, detects timestamp counter resets, groups records by frame, and
identifies observed MMC3 R0–R5 bank writes with their cycle clock values.
Bank registers that have not yet been written remain **unknown**; the
clock offset within a frame is explicitly measured from that frame's
*first logged event*.

Event ordering and relative CPU cycles help detect candidates for
within-frame CHR changes. **CPU clocks alone cannot be accurately mapped to
PPU scanlines** without explicit PPU timing/frame-origin instrumentation,
and writing a bank register during a frame is not itself proof that it
changed a visible pixel. In particular, do not infer a constant scanline
duration from the frame label.

The capture script and analyzer are covered by a synthetic FCEUX Lua mock
and ROM-free Python tests in the regular native-core CI.

## Next verification gate

1. Execute the script inside the actual FCEUX instance with the owner ROM.
2. Record title → first-stage transition; check log completeness and
   whether a CPU-cycle clock was available.
3. Cross-check captured RGB/palette pixels with
   `tools/compare_rendered_frame.py` and compare candidate MMC3 bank
   switch cycles to observed graphical change lines.
4. Investigate exact PPU scanline/dot timestamps before claiming an
   authentic scanline-specific first-stage composition.

All captures, rendered frames, logs, and derived proprietary game-data
reports must remain in the ignored `private/` folder and outside GitHub.

FCEUX API documentation: https://fceux.com/web/help/LuaFunctionsList.html
