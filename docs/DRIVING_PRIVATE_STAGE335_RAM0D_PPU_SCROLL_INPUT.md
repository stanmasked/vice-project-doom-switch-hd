# Stage 335–336 — direct RAM-to-PPU scroll-input dataflow

The owner-private source capture was replayed with the original ROM and matching FM2 in FCEUX 2.6.5, with the movie in read-only mode. The capture covered 261 continuous frames. The original ROM, FM2, raw traces, source hashes, instruction addresses, and byte values remain private.

## Verified observations

- All 1,010 observed writes to PPU register $2005 were matched to executed CPU store instructions.
- All 619 observed writes to RAM $0D were attributed to live CPU instructions; the instruction-effect checks had no mismatches.
- The shared PPU $2005/$2006 write-toggle state was replayed without a mismatch in the captured event stream.
- The first scroll-store path loaded RAM $0B into A and then wrote A to $2005. This was observed and checked 253 times.
- The second scroll-store path loaded RAM $0D into A and then wrote A to $2005. This was observed and checked 253 times. The source byte remained unchanged between the load and the bus write.
- For all 253 second writes, the bus value matched the live RAM $0D byte at the write time. The toggle phase was the second half of the shared scroll-write sequence, corresponding to the Y-scroll input.
- A comparison against the previous frame's end-of-frame sample had one mismatch. The event-order replay explains it: RAM $0D changed multiple times earlier in that same frame, so the live value at the PPU write differed from the previous frame's final sample.

The public aggregate and validator are in `stage335_public_aggregate.json` and `tools/audit_public_stage335_aggregate.py`. CI checks the redacted aggregate only; it does not download or consume private source assets.

## Interpretation boundary

This establishes the direct load/store path for the observed PPU scroll-input writes. It does **not** yet prove effective raster scroll across the full frame, camera speed, world-space road geometry, or collision physics. Those remain separate research tasks. No changes to gameplay physics are justified by this result alone.
