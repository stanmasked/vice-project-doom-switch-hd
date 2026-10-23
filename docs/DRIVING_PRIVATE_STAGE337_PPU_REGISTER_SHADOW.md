# Stage 337 — write-side PPU register shadow audit

This stage uses the previously sealed owner-private Stage335 FCEUX 2.6.5
source trace, **not** a newly invented movie or a substitute for the original
ROM/FM2. The private input was retrieved from the owner-only Google Drive
archive, checked against its existing sealed Stage335 manifest, and analyzed
locally. Neither the ROM/FM2 nor raw register values/PCs are included in Git.

The audit independently replays the **CPU-written PPU register state** using
the ordered source events: PPUSTATUS `$2002` reads, PPUCTRL `$2000` writes,
PPUMASK `$2001` writes, PPUSCROLL `$2005` writes, and PPUADDR `$2006` writes.
It checks the shared PPU write toggle `w` before and after every observed
relevant event. It also tracks `t`, fine X, and CPU assignments to `v`
following the second PPUADDR write, without exporting the private values.

Original-source results, frames **380–640**, inclusive (261 frames):

- 21,398 original-source event rows read in frame and CPU-event order.
- 10,172 PPUSTATUS reads; 844 PPUCTRL writes; 506 PPUMASK writes.
- 1,010 PPUSCROLL writes: 505 first-phase and 505 second-phase.
- 6,096 PPUADDR writes, including 3,048 second-phase CPU address assignments.
- PPUSCROLL writes occurred in 253 of 261 frames: 252 frames with four writes,
  one frame with two, and eight frames with none.
- **Zero write-toggle mismatches** when reprocessing the complete relevant
  CPU event stream. The Stage335 baseline guard passed on the sealed trace.

The new tool is `tools/audit_private_ppu_register_shadow.py`; unit tests in
`tests/test_private_ppu_register_shadow.py` are **synthetic only** and reject
broken event order, incomplete frame coverage, illegal byte values, incorrect
write-toggle phases, and unsupported event schemas. The redacted source
aggregate is in `docs/stage337_public_aggregate.json`.

## Reproduction — private source only

The original Stage335 trace must stay on the owner's private workstation or
Drive-backed local workspace. Run this with an authenticated, independently
verified copy of the sealed Stage335 trace:

```sh
python tools/audit_private_ppu_register_shadow.py \
  --input /private/Stage335/stage335_ppu_latch_ram0d_events.tsv \
  --require-stage335-baseline \
  --output /private/Stage337/stage337-aggregate.json
```

The source TSV's SHA-256 and full-file identity should first be verified
against the **private** Stage335 manifest. The tool refuses any mismatched
Stage335 aggregate counts when the baseline flag is set; it never needs the
original ROM/FM2 bytes to replay the already captured CPU-visible events.

## Strict interpretation boundary

**This is not effective raster scroll.** During rendering, the NES PPU
increments `v` and reloads horizontal/vertical `v` fields from `t` at
specific scanline/dot phases. Those hardware-side changes are not present
in the Stage335 CPU register-bus trace. Although second `$2006` writes
immediately assign the CPU write-side `v`, the simulator's shadow must **not**
be presented as the actual PPU fetch address throughout a scanline.

The next evidence gate is a timed scanline/dot-level PPU capture, or a
separately validated model of hardware reloads and increments cross-checked
against source RGB / video output. Until that gate passes, road position,
camera speed, gameplay collision and full-frame effective scroll remain
**unproven**. No HD driving-physics change follows from this stage.
