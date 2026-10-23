# Stage 325 — private RAM $25/$26 indirect-access trace

An exploratory private FCEUX 2.6.5 probe was run against the owner-provided
Vice: Project Doom ROM and the reconstructed read-only FM2 assembled from
the supplied chunks. The reconstructed movie contains 43,652 controller
records; its embedded cartridge-payload checksum matches the ROM. Source
files and the raw trace were checked locally and remain outside GitHub.

The bounded source window is zero-based FM2 frames 600–920, inclusive.

## Aggregate observations

- 321 source frames were processed.
- 22,146 writes to zero-page RAM $25 were observed.
- 31,474 writes to zero-page RAM $26 were observed.
- 20,524 executed indirect instructions used the $25/$26 pointer pair:
  20,508 were \`LDA ($25),Y\` and 16 were \`ADC ($25),Y\`.
- At least one such indirect access occurred in 319 frames. Frames 601 and
  603 had no matching access during this window.
- In 13,897 intervals between consecutive indirect accesses, at least one
  write to $25 or $26 occurred between those accesses.

The raw trace contains 74,144 write/access events. It records instruction
context, cycle order, pointer bytes and effective addresses locally. The
private manifest binds the ROM, reconstructed FM2, trace and aggregate
summary with full-file SHA-256 digests. No digest, pointer byte value, raw
effective address, source path or raw trace is published.

## Interpretation correction

The counts do **not** support a blanket conclusion that values written to
$25/$26 are always overwritten before the next indirect read. The trace
contains recurring sequences where the pair is written and then consumed by
an indirect read before later instructions transform the pair for a subsequent
read. Other routines modify one or both bytes between accesses.

The 13,897 count is only a temporal metric: it means at least one pointer-byte
write occurred between adjacent indirect-access events. It does not by
itself prove that a table value was lost, identify the table, or assign a
semantic role to $25/$26.

## Next stage

1. Cluster the trace by live execution site and mapper-bank context.
2. Separate pointer initialization, pointer transformation and indirect-read
   call sites instead of aggregating all $25/$26 activity together.
3. Compare the observed effective-address ranges with the verified
   \`($AA),Y\` source decoder and its writes to RAM $0B–$0D.
4. Keep effective PPU scroll, world-space road geometry, camera speed and
   collision physics marked unproven until a reproducible cross-layer
   relationship is established.

This stage is exploratory reverse-engineering evidence, not a game-logic
implementation change. The raw trace and original inputs remain private.
