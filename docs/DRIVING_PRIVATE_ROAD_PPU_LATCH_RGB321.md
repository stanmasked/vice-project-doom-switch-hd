# Stage 322 — one-session road/CPU/PPU/RGB capture

Stage 321 established a private PPU register trace in a separate FCEUX
process. Stage 322 captures the source road image, CPU writers, post-frame
RAM and actual PPU-port events during the same read-only FCEUX 2.6.5
session, then seals all seven raw evidence files against the full ROM/FM2
file identities.

Owner-local command (use a new directory outside every Git checkout):

    python3 tools/run_private_road_ppu_latch_rgb321.py --rom /private/owned_original.nes --movie /private/owner_movie.fm2 --output-dir /private/new_same_session_road_ppu_rgb

The runner checks source identity before launch, verifies the FM2 is
read-only in FCEUX, waits for the complete 600–920 frame window, checks
source identity again, validates all evidence, and seals the capture. It
does not upload the ROM, FM2, raw RGB, CPU values, event rows, private paths
or full-file hashes.

Original-source result:

- 321 consecutive frame-clock rows covering source movie frames 600–920.
- 1,284 CPU-side $2005 writer instructions and 1,284 actual $2005 bus writes,
  matching on both values and CPU-cycle timestamps.
- 10,203 PPU register events: 845 direct PPUSTATUS read candidates, 808
  PPUCTRL writes, 642 PPUMASK writes, zero PPUSTATUS writes and 6,624
  PPUADDR writes.
- 321 post-frame RAM $0D samples and 41 raw RGB road slots at frames
  600, 608, …, 920, sampled in the same post-frame callback.
- Every frame retains latch roles 0, 1, 0, 1; no captured PPUSTATUS
  read candidate or PPUADDR write interrupts adjacent $2005 writes.
- The CPU writer, RAM sample and RGB payload reproduce the previously
  sealed independent captures byte-for-byte; all 1,284 CPU/PPU writer
  values and cycles also match inside this combined session.

Only aggregate counts are printed. The raw RGB and event data remain in the
private capture directory, and the source seal binds all seven evidence
files to the original ROM/FM2 SHA-256 identities.

The capture joins image-space scanlines, CPU writer events, RAM samples and
actual PPU register writes to one source frame clock. It does not yet prove
effective PPU raster scroll, camera velocity, world-space road geometry or
collision physics. The older Stage 170 road report remains a separate
hashless comparison target; this stage does not retroactively authenticate it.

Public Python and Lua CI fixtures use synthetic data and do not contain or
replay the owner's ROM/FM2.
