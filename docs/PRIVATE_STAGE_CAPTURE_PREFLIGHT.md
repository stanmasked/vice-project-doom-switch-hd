# Private FCEUX first-stage capture preflight

**Purpose.** Before using any original-game FCEUX records to measure the
first playable stage, establish that the capture session is internally
consistent and files were neither truncated nor mixed across ROM images.

This is **local-only** preparation. The tool does not download a game,
does not run FCEUX, does not measure scroll, does not prove that a file
was captured from an actual NES game and does not recover collisions or
native Switch gameplay. Its output deliberately excludes original ROM
MD5 values, PPU bytes, graphics, RAM and palette contents.

## Running it against an owner's private capture

1. Open your personally owned copy locally in FCEUX and follow
   [REFERENCE_CAPTURE.md](REFERENCE_CAPTURE.md). Keep the PPU/RAM and
   optional screen recordings in an ignored directory such as
   `private/first_stage/` — **never commit those data**.
2. Run the preflight locally:

   ```sh
   python3 tools/audit_private_fceux_capture.py private/first_stage
   ```

3. Only after the result `PRIVATE_FCEUX_CAPTURE_PREFLIGHT_PASS`, verify
   game scene identity, **independently measure camera and scroll**,
   prepare the evidence-gated manifest from
   [STAGE_MAP_EVIDENCE.md](STAGE_MAP_EVIDENCE.md) and run the tile
   mosaic tool.

The tool searches `frame_*.meta.txt` and checks the exactly paired
`frame_NNNNNN.ppu.bin` (16384 bytes), `ram.bin` (2048 bytes),
and when `screen_reference=yes` both the 256×240 RGB and 8-bit palette
files. It checks real FCEUX 2026-current v3/v4 metadata contracts,
matching frame filename and number, six-digit-or-longer frame numbering,
consistent FCEUX-provided ROM hash within one session without outputting
it, recorded sampling interval and cap, cumulative event counter,
strictly non-symlink capture roots, no mixing v3/v4 capture schemas,
and for v4 a consistent CPU-cycle trace availability flag and explicit
`debugger_since_reset` counter epoch,
all-or-none screen mode, monotonic cumulative lost-write counts, zero\nunavailable-color count when screen recording is disabled, no stray/unpaired\nframe files, valid NES screen
palette indices (0..63 or unavailable sentinel 254), and exact counts of
unavailable palette samples.

By default any lost register writes invalidates the session. For archival
triage only, `--allow-incomplete` keeps a visibly flagged report with
`all_register_logs_complete=false`; it **does not** allow you to claim a
verified first stage, exact PPU timing or renderer fidelity.

Example **fictional** summary:

```text
PRIVATE_FCEUX_CAPTURE_PREFLIGHT_PASS
{
  "classification": "private ROM capture metadata/length preflight only",
  "capture_count": 2,
  "first_frame": 120,
  "last_frame": 240,
  "screen_reference": true,
  "cycle_trace_available": false,
  "all_register_logs_complete": true,
  "incomplete_frame_count": 0,
  "fceux_rom_identity_consistent": true,
  "private_capture_authenticity_proven": false,
  "actual_first_stage_proven": false,
  "camera_scroll_measured": false,
  "first_stage_geometry_recovered": false,
  "next_step": "Privately verify stage and independent camera/scroll provenance, then assemble map manifest."
}
```

A PASS means **file consistency**, not source authenticity. The checker
cannot detect semantically false camera RAM values, midframe CHR swaps,
synthetic but consistent files, or inaccurate FCEUX Lua APIs. Reconstructed
tiles must remain private alongside original gameplay recordings.
No captures, exported sprites or commercial ROMs belong in GitHub or CI.

All **42 Python tests** fabricate private captures in temporary
directories. No NES images, copyright artwork or original-game ROM
identity is stored in this repository.

## Stage 107 — provenance hardening

The v4 verifier rejects missing or contradictory CPU-cycle trace declarations,
unsupported counter epochs, or mixed clock availability within one capture
session. These are consistency checks, not evidence that a clock trace really
exists or proves effective scroll, CHR timing, or game authenticity. The
legacy v3 format remains accepted without these two fields and reports
`cycle_trace_available=null` (unknown). A symbolic-link capture root is
rejected to avoid accidentally analyzing a different directory.

Seven additional invented-data regression tests cover these rejection cases,
v3 backwards compatibility, and the root-path guard. Neither the original
ROM nor any extracted frame data is required in GitHub Actions.

## Stage 108 — verify real register TSV evidence, not metadata alone

The default command remains **metadata-only** and now explicitly returns
`register_trace_verified=false`. For a session where register-log evidence
will be used to reconstruct PPU scrolling, run the stricter mode:

```sh
python3 tools/audit_private_fceux_capture.py private/first_stage --require-logs
```

This checks the actual private `mmc3_video_writes.tsv` against each sampled
frame's cumulative `logged_register_writes` counter; event frame ordering,
register address and byte syntax; FCEUX's maximum 250,000 logged events;
and size-bounded, regular (non-symlink) trace files. If v4 metadata declares
`cycle_trace_available=yes`, the companion `mmc3_ppu_cycles.tsv` becomes
mandatory, and every row must correspond to the same video-log event with a
plausible CPU-cycle number and read/write label. Declaring no clock while
leaving a cycle file also fails, preventing accidental stale-session mixing.

The report contains only `register_trace_verified`,
`cpu_cycle_trace_verified` and an aggregate `verified_register_events`
count; **no register values, ROM hash, or original video content are printed**.
A verified TSV is still neither proof of authentic source-game execution nor
proof of exact raster timing: FCEUX counter reset behavior, scanline splits,
and effective world camera require separate private investigation.

Twelve initial invented-data tests cover valid event and clock logs plus missing,
truncated, reordered, unexpected, mismatched, or stale logs. Combined with
the previous 26 tests and four Stage 109 tests, 42 synthetic regression tests are present; their
latest GitHub Actions result must be checked independently before marking
this PR ready for review.

## Stage 109 — per-frame logger limits and post-capture evidence

The strict TSV verifier now checks both documented native FCEUX limits:
250,000 recorded events per session **and 12,000 per frame**. Traces that
exceed the per-frame limit fail the audit even if the metadata counts
were manipulated to agree with them.

A real capture can legitimately continue logging **after its final sampled
frame**, so the auditor validates those trailing rows but only matches the
cumulative metadata counter at the sampled frame boundary. All trailing
rows must still have valid addresses and compatible CPU-cycle entries.
The synthesized test suite adds four cases: per-frame overflow,
valid post-capture tail, malformed post-capture tail, and forged
PPUSTATUS read/write markers. The dedicated preflight suite now contains
**42 ROM-free test methods**; do not equate source-level test presence
with completed GitHub Actions or a real first-stage capture.
