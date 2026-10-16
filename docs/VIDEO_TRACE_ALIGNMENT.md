# Stage 39 — correlate dispatcher trace with first-level video

**Status: alignment utility delivered; authentic first-level video and FCEUX
execution logs have not been supplied or captured here. No first-stage map,
camera semantics, collision positions or level loader are claimed recovered.**

The tool `tools/align_dispatch_video.py` takes (1) the private stage-38
FCEUX TSV plus its metadata and (2) a manually verified CSV of synchronized
video and emulator frames. It **first runs the stage-38 fail-closed audit**,
including completeness and MMC3 bank-state checks. This is not a substitute
for recording a genuine session.

In a private Git-ignored folder, create `anchors.csv`:

```csv
video_frame,trace_frame,label
120,231,first_gameplay_frame
180,291,first_camera_motion
260,371,visible_spawn
```

**These frame numbers are illustrative only, not real observations.**
Use real measurements from the original video and the same FCEUX playback.
Frames in both columns must increase strictly. The video frame clock is
not guaranteed to equal `emu.framecount()`; the tool intentionally does not
infer synchronization, frame-rate ratios or discontinuities.

```sh
python3 tools/align_dispatch_video.py \
  private/first_level/stage38_dispatch_exec.tsv \
  private/first_level/anchors.csv \
  --meta private/first_level/stage38_dispatch_exec.meta.txt \
  --radius 1 \
  --out private/first_level/stage39_alignment.json
```

Each anchor reports nearby execution callbacks, mapper events and tracked RAM
writes, physical PRG mapping when proven, and sampled $07/$90/$91/$92 and
$AA/$AB/$A8/$A9 bytes. These snapshots may be pre-write observations;
they are not automatically final RAM values. In particular, an indexed
$E479/$E4E6 execution or an MMC3 R6/R7 value does not by itself establish
which stage chunk was loaded or whether a variable is camera X.

Required next real-world evidence: use the owner's local ROM in FCEUX, record
a continuous actual first-level trace without dropped events, preserve the
independent video reference and explicit anchors, then examine correlated
changes around player movement, scrolling, loader transitions and bank writes.
Compare candidate byte streams against independently observed PPU screens
before naming collision or stage geometry. Never commit game assets, ROM
dumps, original frames or trace artifacts containing extracted game data.

## Capture-window diagnostic (stage 39 hardening)

The JSON now includes `trace_recorded_frame_span`, plus per-anchor
`trace_frame_within_recorded_span` and `anchor_has_instrumented_events`.
An anchor outside the recorded span is not corroborated by the trace.
An in-range anchor with zero callback events is **not** proof that the
original game was idle; the logger observes selected addresses only.
Even a completely valid synthetic test cannot establish video identity.

GitHub Actions is configured to run `test_video_trace_alignment.py`
explicitly, but the result is not considered verified until a passing
workflow run or a locally executed test report is available.
