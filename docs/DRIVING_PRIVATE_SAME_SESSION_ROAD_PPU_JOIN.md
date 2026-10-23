# Stage 323 — fresh same-session road/PPU numeric join

The Stage 322 capture now supports a separate source-derived image/CPU
alignment step. The join command first verifies the sealed original ROM/FM2
identity and all seven same-session artifacts. It then derives two numeric
documents in memory only: accepted image-space road intervals from the raw
RGB slots, and 321 CPU writer/RAM/frame-phase records from the same FCEUX
session.

Owner-local command:

    python3 tools/audit_private_same_session_road_ppu_latch_rgb321_join.py --rom /private/owned_original.nes --movie /private/owner_movie.fm2 --private-dir /private/new_same_session_road_ppu_rgb

Original-source result:

- 41 source RGB slots, 37 accepted intervals and four explicitly ambiguous
  slots (712, 720, 728 and 736). No missing boundary is interpolated.
- 321 CPU/PPU frames and 1,284 source writer events joined to the same
  frame clock and post-frame RAM samples.
- Four previously published road/PPU/RAM anchor pairs match.
- The ROM and FM2 full-file SHA-256 identities in both ephemeral numeric
  documents match the capture seal.
- The numeric documents are not written to disk or printed.

This validates the fresh image-space road interval alignment against the
observed CPU/PPU/RAM trace. It does not prove effective PPU raster scroll,
camera speed, world-space road geometry or collision physics. The older
Stage 170 report remains hashless; this join does not retroactively
authenticate it, and the strict legacy-exact-reproduction gate remains
separate.

Public tests synthesize RGB pixels, CPU rows, RAM samples and clocks; they
do not contain or replay the owner's ROM/FM2.
