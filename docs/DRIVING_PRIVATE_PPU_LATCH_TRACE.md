# Stage 321 — original PPU write-latch trace

This stage extends the private FCEUX investigation from CPU-side $2005
writer values to actual PPU-port writes and the shared $2005/$2006
write toggle. It is a separate bounded capture over original movie frames
600–920. It does not replace the sealed same-session RGB/CPU capture and
does not authenticate the older hashless road report.

## Owner-local capture

Run only with the owner's original local ROM/FM2 and an installed real
FCEUX 2.6.5 executable. The output directory must be new and outside Git:

    python3 tools/run_private_ppu_register_latch_321.py \
      --rom /private/owned_original.nes \
      --movie /private/owner_movie.fm2 \
      --reference-capture /private/sealed_road_ppu_capture \
      --output-dir /private/new_ppu_latch_trace

The runner verifies complete ROM/FM2 file identities before and after the
capture, runs FCEUX read-only, seals the event stream and its frame clocks,
and cross-checks all 1,284 actual $2005 port values against the separately
sealed CPU writer trace. Original ROM/FM2, event rows, paths and digests are
never copied to GitHub or printed.

## Private original-source result

Two independent full candidate-hook captures produced byte-identical event
streams. The final capture includes 321 continuous source-frame clock rows
and 10,203 PPU-register events. The redacted audit reports:

- 321 source frames and 1,284 $2005 writes.
- 845 direct PPUSTATUS read candidates, 808 PPUCTRL writes, 642 PPUMASK
  writes, zero PPUSTATUS writes and 6,624 PPUADDR writes.
- Every frame's four $2005 writes observed with shared-latch roles
  0, 1, 0, 1.
- No captured $2002 read candidate or $2006 write between adjacent
  $2005 writes.
- All 1,284 actual $2005 values matched the sealed CPU instruction trace.

The PPU bus-write callback's program counter is not used as the
instruction identity: four dedicated execution hooks validate the live
STA/STX $2005 instruction bytes, latch the A/X value before execution, and
bind the later actual bus write to that instruction's post-PC. The auditor
still independently checks all 1,284 port values against the sealed CPU
writer trace.

Writes outside frames 600–920 are ignored before the window-specific writer
witness is checked; the game also writes PPUSCROLL during its earlier startup.

The installed FCEUX build does not expose memory.registerread. Therefore
the capture hooks every direct/indexed $2002 reader candidate found by a
static scan of the original PRG banks, checks the live instruction bytes,
and only accepts indexed candidates when the index register is zero. This
is stronger than assuming every read is LDA $2002, but it is not a proof
that the game never performs an indirect I/O read or executes code copied
to RAM. The audit deliberately calls these direct read candidates.

## What this proves—and does not

The trace validates how the observed CPU writes interact with the shared
PPU address/scroll toggle. It does not read internal PPU v/t scroll state,
identify exact raster scanlines, or prove effective display scroll, camera
speed, world-space road geometry or collision physics. The new trace was
captured in a separate FCEUX process from the RGB samples, so no
within-frame RGB/raster join is claimed.

Stage 322 now captures PPU-register events, CPU/RAM samples and RGB road
scanlines in one sealed original-source FCEUX session. See
`docs/DRIVING_PRIVATE_ROAD_PPU_LATCH_RGB321.md`. The strict legacy report gate
remains separate until its missing source identity can be established.

Public CI tests use invented mock events and do not contain or replay the
owner's ROM/FM2.
