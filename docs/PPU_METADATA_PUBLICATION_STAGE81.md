# Stage 81 — verified metadata publication for FCEUX PPU sessions

## Defect and failure boundary

Prior to stage81, `tools/capture_fceux_ppu.lua` opened both the
per-frame metadata and finalized session manifest directly with `wb`,
truncating the pending marker. The generic `write_binary` function
checked `write()` but did not check `close()`. A crash, short write
or delayed disk error could therefore leave partial metadata containing
a misleading `complete=yes` while the frame or session was incomplete.

Stage81 moves the finalization of both kinds of metadata behind a
verified temporary-file publication boundary. Regular PPU/RAM binary
writes also now check the result of `close()`.

## Finalization protocol

`publish_metadata(path, contents)`:

1. Requires the destination to exist and match **exactly**
   `capture_in_progress=yes\\n` (a prior valid file is not accepted).
2. Writes `path.tmp` in the same directory and checks the write and
   close operations.
3. Reopens `path.tmp`, compares its complete bytes with the expected
   contents, and checks that its read handle closes successfully.
4. Removes the **pending** destination only after successful readback.
   This supports Windows-like filesystems where rename cannot replace
   an existing file.
5. Renames the verified temporary file to the destination. If this
   fails, the destination is **missing** instead of falsely completed.

All tested failure paths return an error. Before the publication
boundary, the pending marker remains intact; after a failed rename,
the file is absent. Either state must be rejected by the strict
session validator. A leftover file with `.tmp` is never treated as
published metadata.

This is intentionally **fail-closed publication**, not a claim of
atomic replacement across arbitrary crashes or power failures. There
is a short missing-file window between removing the pending marker
and renaming the temporary file, and no OS-level `fsync` is performed.
A hard crash or delayed storage corruption still requires external
backup and an independent recheck.

## Verification

`tests/test_fceux_ppu_metadata_publication.lua` extracts the **exact**
production `publish_metadata` function from the Lua collector using
`load`, and injects failures into file operations, without loading
any real ROM, screen or emulator code.

It checks ten isolated cases:

- temporary open failure
- temporary write failure
- temporary close failure
- readback content mismatch
- readback close failure
- pending-marker removal failure
- final rename failure
- refusal to publish over metadata that is not pending
- successful publication of frame metadata
- successful publication of finalized session metadata

**10/10 passed locally** with LuaTeX's Lua interpreter. For extra
assurance, the locally executed test file and extracted production
function were compared with GitHub's exact file contents: UTF-8
lengths and FNV-1a 32-bit checksums matched. This is a faithful
source-level unit test, but the **full FCEUX Lua collector's runtime
and actual SD/disk behavior are not live-tested**.

The new test is wired into the `code-and-tests` GitHub Actions job.
An Actions run is evidence only when its jobs actually execute:
previous runs have repeatedly failed before runner allocation.

No original game resources, map geometry, screen capture or Switch NRO
were created or checked into GitHub.
