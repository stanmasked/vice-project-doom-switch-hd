# Stage 324 — same-session RAM $0D write trace

Stage 324 adds a bounded write hook for zero-page RAM address $0D to the
existing original-source FCEUX capture. The hook records the actual write
cycle, pre/post byte, live A/X/Y registers, and the executed instruction
bytes around the callback PC. These raw records stay in a new private
capture directory and are sealed separately while bound to the already
sealed CPU/PPU/RGB capture and its full ROM/FM2 file identities.

Owner-local command (use the original files and a new directory outside Git):

    python3 tools/run_private_road_ppu_latch_rgb321_ram0d.py --rom /private/owned_original.nes --movie /private/owner_movie.fm2 --output-dir /private/new_ram0d_same_session

The auditor verifies all 321 frame clocks, 1,284 CPU writers, 321 post-frame
RAM samples, the base capture seal, and the additional RAM-write seal.
It also checks the live instruction bytes and write effects, per-frame
old/new chains, and the relationship between the second $2005 writer and
the previous frame's RAM sample.

Original-source result from FCEUX 2.6.5:

- 1,506 writes to RAM $0D in the 321-frame window.
- 1,500 writes were executed as DEC $0D; six were STA $0D.
- Every observed write's value matched its instruction effect; frame-level
  old/new chains and post-frame RAM samples were consistent.
- The second $2005 writer matched the previous frame's post-frame RAM $0D
  in 319 of 320 comparisons. The sole mismatch is at the initial window
  boundary, frame 601.
- The seven existing CPU/PPU/RGB source artifacts reproduced the previous
  sealed capture byte-for-byte; the added RAM trace was recorded during
  this new same-session run and sealed against the base capture seal.

This establishes a repeatable temporal relationship, not a semantic name:
RAM $0D is not yet declared to be the effective PPU scroll or camera
position. Effective raster scroll, world-space road geometry, camera speed
and collision physics remain unproven. No original ROM/FM2, raw byte values,
RGB pixels, source paths or private hashes are committed.
