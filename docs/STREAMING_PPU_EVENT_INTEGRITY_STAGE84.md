# Stage 84 — streaming PPU event integrity for long captures

## Performance defect

Stage83 made TSV checksums part of the evidence chain, but the FCEUX
collector reread each growing TSV from byte 0 **at every saved frame**.
With `K` snapshots and an eventually `L`-byte log, cumulative
readback could approach `O(K × L)` rather than `O(L)`.
The session limit allows 512 snapshots and 250,000 events, so this
extra work was material and unnecessary.

## Improved capture path

`tools/capture_fceux_ppu.lua` now maintains independent incremental
Adler-32 `(a,b)` accumulators, initialized using each TSV's exact
header bytes. After a successful write+flush of a batch, it advances
these accumulators by **only the newly written bytes**. A snapshot's
`frame_log_prefix_adler32` and `cycle_log_prefix_adler32` are
read directly from the accumulated state: no additional TSV read is
required during snapshot capture.

At exit the collector still:
1. Flushes any pending events and closes both logs.
2. Independently reads **each entire TSV once** in 65,536-byte chunks.
3. Calculates fresh Adler-32 digests from actual bytes on disk.
4. Rejects the session if either result differs from its rolling
   checksum. The manifest remains pending on error.
5. Publishes the validated session manifest using stage81's
   temporary-file/readback protocol.

A failed cycle-log write cannot advance both rolling accumulators
as though the flush succeeded. A failed capture cannot be upgraded to
`complete=yes`. The stage79/83 Python validator still independently
compares the complete bytes and every captured frame's prefix.

This is an improvement in asymptotic repeated **disk I/O**, not a
claim of cryptographic provenance or crash-safe filesystem commits.

## Python verifier

`tools/verify_ppu_capture_session.py` also computes TSV digests
incrementally, iterating over binary lines instead of calling
`Path.read_bytes()` and keeping an extra duplicate of the whole TSV
in memory. It retains the per-event prefix checksum list required
for snapshot validation, so its overall memory use is **O(E) for E
events**, not constant. The raw-file duplication was removed.

## Verification

- The exact streaming Python verifier and tests committed to GitHub
  have been run locally: **44/44 synthetic tests passed** (37 prior
  plus 7 new).
- The additional tests cover **24,000 synthetic events**, including
  independent checks of selected intermediate digests; they reject
  same-size corruption, extra rows, truncation, missing files and
  incorrect headers. One test explicitly forbids `Path.read_bytes`
  inside the streaming checksum helper.
- The production-equivalent Lua checksum helpers were exercised
  locally in LuaTeX over 24,000 synthetic events. Its bounded
  64 KiB readback was checked, checksum matched incremental state,
  and an unchanged-length byte edit changed the checksum. An initial
  bug in the test's monitored path was found and fixed before
  the successful run.
- `tests/test_fceux_ppu_checksum_streaming.lua` loads the **actual**
  helper functions from the checked-out production Lua file and runs
  the same stress assertions. The stage83 collector integration mock
  was extended to verify **zero** event-log readbacks during snapshot
  capture, exactly **one** readback per available log at exit, and
  refusal to publish a session after simulated final TSV corruption.
  Both tests are committed to GitHub Actions, but complete live
  execution against that checkout is **not yet confirmed**.

## Boundaries

No actual Vice: Project Doom ROM, game screenshot, authenticated map
geometry, original first-stage video trace or Switch NRO was obtained.
Checksums detect accidental damage, not malicious alterations.
Independent FCEUX and Switch hardware tests remain outstanding.
