# Stage 83 — full TSV and per-snapshot prefix integrity

## Defect and objective

Stage82 checks saved PPU/RAM/RGB/palette binary contents against per-frame Adler-32 checksums. The two **event streams** (`mmc3_video_writes.tsv` and optional `mmc3_ppu_cycles.tsv`) previously had structural/count/cross-row checks, but no byte-level digests. A same-size change to a CPU-cycle timestamp could preserve all event counts and frame/address/value comparisons without being detected.

Stage83 adds two levels of checksum evidence. The metadata remains private; neither checksum authenticates the commercial game's data.

## Producer: `tools/capture_fceux_ppu.lua`

After flushing the logs **and before writing snapshot metadata**, the collector reads back the on-disk TSV bytes, checks newline termination and calculates:

```text
event_checksum=adler32_v1
frame_log_prefix_adler32=<uppercase 8-digit Adler-32>
cycle_log_prefix_adler32=<uppercase Adler-32 or not_captured>
```

The frame metadata also already contains the exact `logged_register_writes` checkpoint from stages 79–82, plus the checksums of its PPU/RAM/screen data.

At session shutdown, after both event streams have been closed successfully, it rereads and hashes their **entire saved contents**, publishing in the finalized session manifest:

```text
event_checksum=adler32_v1
frame_log_adler32=<uppercase 8-digit Adler-32>
cycle_log_adler32=<uppercase Adler-32 or not_captured>
```

If a readback or checksum operation fails before finalization, the per-frame or session metadata remains pending and must not be accepted as verified evidence.

## Independent verifier

`tools/verify_ppu_capture_session.py` recomputes the Adler-32 of the **raw TSV bytes, including header and newline characters**. It verifies the declared digest for each full event log and derives the checksum after every event row. A frame snapshot with checkpoint N is accepted only when its recorded prefix checksum matches **header plus exactly N event rows** in both logs.

This blocks mismatches between snapshots and their supposedly corresponding event history, including a TSV which has the right row count but changed CPU-cycle bytes. For no-cycle sessions, both metadata layers must explicitly contain `not_captured` for the cycle checksum.

The original stage79 event-to-event cross-check and stage82 saved PPU/RAM checksum validation remain mandatory.

## Test evidence

- **37/37 locally executed synthetic Python tests passed**, including 13 newly covered TSV-corruption and prefix-binding cases. The locally tested file hashes match the exact GitHub blobs:
  - `tools/verify_ppu_capture_session.py` — `a2aa2b854a14dfb2dc8226e0fc960bd1977750f0`
  - `tests/test_ppu_capture_session.py` — `baa4a5102ffd5dc45064898679338ff528580368`
- Tests reject same-length event data corruption, same-length CPU-cycle timestamp changes, missing/malformed log checksum metadata, truncated TSV, altered prefix digests, and a recalculated full checksum that does **not** agree with previous frame checkpoints.
- Added `tests/test_fceux_ppu_event_log_checksums.lua` running the actual production FCEUX Lua collector with invented events over two frames, both with and without a synthetic cycle counter. It compares real stored prefix and final metadata digests against independently recomputed Lua Adler-32. It is wired into the native GitHub Actions job, but **has not been confirmed to pass in the full checkout**.

## Limits

Adler-32 detects accidental corruption; it is not collision-resistant and does not provide tamper-proof provenance. This stage does not confirm original ROM identity, PPU scanline timing, level-map geometry, real FCEUX execution or a working Nintendo Switch NRO. Capture artifacts must remain private and untracked.

Reading full TSV files at each selected snapshot can be expensive for long sessions; the existing event and capture limits still apply. If the platform forbids reading a file while it remains open for writing, the collector will fail closed rather than publish unverifiable metadata.
