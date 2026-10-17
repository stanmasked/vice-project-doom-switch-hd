# Stage 79 — full-session FCEUX video capture integrity

## Problem

Stage76 protected individual frames from stale metadata, and stages77–78
extended the video hook coverage. But `register_log_complete=yes` in
`frame_NNNNNN.meta.txt` only described the **prefix of the event log
available at that moment**. A later drop, invalid callback, failed
snapshot, crash or skipped callback frame could leave early snapshots
looking complete. Those snapshots cannot certify a whole-session video
trace.

## Capture protocol

`tools/capture_fceux_ppu.lua` now creates
`private/ppu_capture_session.meta.txt` with

```text
capture_in_progress=yes
```

**before** opening new event streams. Each snapshot retains
`format=fceux_ppu_snapshot_v4` and gains:

- `session_id`: best-effort correlation token (not an authenticity
  signature or cryptographic checksum)
- `session_snapshot_index`: strictly increasing index in this run
- `capture_scope=frame_prefix_only`: per-frame completion does not
  certify the rest of the session

The callback records first/last observed frame, number of distinct
frame callbacks and frame-number discontinuities. A frame snapshot
exception increments `capture_failures` even if FCEUX continues.

After the exit callback has flushed and **closed** the event streams,
the tool writes a finalized `fceux_ppu_session_v1` manifest containing
frame numbers, snapshot count, callback span, event count, drop count,
callback errors and failures, and the full MMC3/PPU callback coverage.

`complete=yes` requires a nonempty snapshot set, **zero** dropped
events, callback errors, capture failures and callback-frame gaps.
If a session crashes before this exit callback, the manifest remains
pending. If a later frame fails, even early `register_log_complete=yes`
snapshots do not make the overall manifest complete.

## Independent session validator

`tools/verify_ppu_capture_session.py` checks:

1. Finalized manifest and declared full MMC3/PPU hook coverage
2. Strict unique metadata keys, token, callback counts and continuous
   frame numbering (including no skipped callback frames)
3. Every captured frame listed once, in order, with matching
   `session_id`, index and valid prefix metadata
4. Presence and exact expected sizes of PPU (16384 bytes), RAM
   (2048 bytes), and optional RGB/palette screen files
5. Exact frame-log event count and nondecreasing event frame numbers
6. For sessions with CPU-cycle data, **event-by-event equality** of
   frame, address and byte in the two TSV logs, including PPUSTATUS
   read markers being type `R` rather than `W`

Example from a private local capture directory:

```sh
python3 tools/verify_ppu_capture_session.py \
  private/ppu_capture_session.meta.txt --require-cycle \
  --out private/verified_ppu_session.json
```

The output is a local evidence-consistency report, not recovered
map geometry. The CPU-cycle analysis CLI now requires
`--session-meta private/ppu_capture_session.meta.txt` in addition to
its per-frame `--metadata`, and refuses metadata from outside that
session. MMC3 frame-log and scroll CLIs accept `--session-meta` for
verification and otherwise label results as diagnostics only.
For scroll analysis, supplying only per-frame metadata is rejected.

## Verification performed

`tests/test_ppu_capture_session.py` contains **17 ROM-free synthetic
regressions** covering successful sessions, stale metadata, aborted or
malformed captures, skipped callbacks, truncated/missing binary files,
dropped events, repeated manifest keys, and mismatched CPU-cycle rows.
All 17 tests **passed locally in Python** using the exact versions
committed to PR #3 (Git blob IDs checked).

The new `tests/test_fceux_ppu_capture_session.lua` exercises the
actual FCEUX capture script using synthetic callbacks, both for
continuous frames `[1,2]` and a gap `[1,3]`. Existing stages76/77
Lua tests now also assert that later errors render the **entire**
session manifest incomplete. These Lua tests are committed and
scheduled in CI but a successful execution in an up-to-date Lua/FCEUX
checkout has **not been confirmed** here.

## Evidence limits

This is a **consistency and truncation guard**, not cryptographic
authentication or bytewise proof that every binary remained unchanged
after capture: binary size checks cannot detect same-size modification.
`session_id` is not a signature. A continuous `emu.registerafter`
frame count does not independently prove physical PPU scanline timing.
Authentic original-game identity, loader behavior, map geometry,
original graphics and Switch NRO remain unverified/unproduced. Never
commit the owner's ROM, screenshots or private capture files.
