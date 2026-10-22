# Stage181: owner-private complete 321-frame CPU $2005 writer trace

The seven known original image-space road references and the
37/4 numeric road-mask report **do not establish effective NES
scroll or physical driving motion**. The full per-frame CPU evidence
for FM2 movie frames **600 through 920** was previously missing.

This optional capture tool uses an owner-controlled, **already loaded
original US ROM** and private readonly FM2 in FCEUX. It requires
exact ROM MD5 verification and exact movie frame count supplied by
the owner; the script does not open, copy or publish game bytes.
Set four environment variables locally:

- `VPD_PRIVATE_PPU321_OUTPUT_DIR`: existing empty private output folder
- `VPD_PRIVATE_FM2_PATH`: owner-only original FM2 input path
- `VPD_PRIVATE_ROM_PAYLOAD_MD5`: verified 32-hex MD5 for the loaded ROM
- `VPD_PRIVATE_FRAME_COUNT`: validated original movie length

Then launch FCEUX with the script and your **local** ROM (never in
public Actions):

```bash
fceux --loadlua tools/capture_private_road_ppu_321.lua /private/owned_game.nes
python3 tools/audit_private_road_ppu_321_trace.py \
  --private-dir /private/road_321_capture \
  --summary /private/new_summary.json
```

The private directory must have no existing output files. The
script stops recording at movie frame 920 and produces:

- `road_321_writers.tsv`: four ordered source CPU store-PC/A/cycle
  observations **per frame** at E8EC,E8F1,E369,E36C
- `road_321_postframe.tsv`: 321 source after-frame RAM $0D samples and
  the actual $2005 registerwrite count
- `COMPLETE.txt`: frame continuity, 1,284 CPU callbacks and port writes,
  runtime ROM MD5 and read-only FM2 assertions, **no ROM or movie hashes**

Independent audit rejects frame, callback, writer-PC, CPU pair-cycle,
published second-write/RAM anchor, counter, schema or attestation
mismatches. The only sharable output is an aggregate summary of
counts and explicit *not proven* flags. Raw CPU cycles, local paths,
the private FM2, ROM and complete original data **stay private**.

The script measures **raw absolute CPU cycles**, not the verified
per-frame cycle phase used by Stage168's independent joining audit.
A subsequent separate and explicitly validated frame-phase conversion
is still required before the Stage169 complete 321-frame PPU/image
joining gate can be claimed. No original execution of this new script
is yet confirmed; public CI uses only fabricated Lua hooks and Python
event tables.
## Stage 182 — FCEUX frame-begin cycle boundary and source phase

The same FCEUX Lua session now also records
`road_321_frame_clock.tsv`: exactly **321** lines containing movie
frame label, source `debugger.getcyclescount()` at
`emu.registerbefore`, and the source count at `emu.registerafter`.

Both hooks exist in upstream FCEUX; this stage deliberately **does not
approximate** a 29.8k CPU frame duration or infer one from the two
writer-PC groups. The validator compares each of the **1,284** CPU
writer callback timestamps against the observed boundaries for the
same 321 frames. It rejects mismatched frames, resets in the counter
epoch, missing/duplicate boundaries, event timestamps outside a
frame, and incompatible early/late source-phase ranges. It still
checks the previously established 7-cycle and 4-cycle write-pair
gaps and 4 previously published original raw-RAM anchor pairs.

After the original owner-private capture, run **both** audit commands:

```bash
python3 tools/audit_private_road_ppu_321_trace.py \
  --private-dir /private/road_321_capture \
  --summary /private/new_raw_summary.json
python3 tools/audit_private_road_ppu_321_frame_phase.py \
  --private-dir /private/road_321_capture \
  --summary /private/new_frame_phase_summary.json
```

All raw CPU cycle counts, private paths and full source values stay
outside GitHub. Outputs contain counts and booleans only.
Successfully evaluating **relative CPU phase** is **not** evidence of
the effective on-screen PPU scroll, collision or original NES camera
speed. A jointly verified ROM/FM2 SHA-256 from separately captured
image-road data is also still required for Stage169's full join.

## Stage 183 — complete file SHA-256 provenance and local FCEUX runner

`tools/run_private_road_ppu_321.py` now supports a **single local
command** that validates the owned NES ROM and FM2 before launch,
verifies that the FM2 begins from power-on and matches the cartridge
payload checksum, and computes SHA-256 over **entire ROM and FM2 files**.
It starts the original-only FCEUX 321-frame Lua script in a new
private directory, waits for the complete original 321-frame witness,
verifies all 1,284 writer CPU events and actual within-frame timing,
and then compares the exact ROM/FM2 SHA-256 digests again.

For a successful session the private directory contains two additional
**strictly local** manifests: `SOURCE_IDENTITY_BEFORE.json`
and `SOURCE_IDENTITY_SEALED.json`. The latter seals SHA-256 of all
four raw report files (including `COMPLETE.txt`) to the complete
ROM+FM2 file identities; any input or capture tampering fails the
independent audit. Neither manifest, SHA-256 values nor raw source
reports are printed or committed to GitHub.

Example (replace with your personally owned private files):

```bash
python3 tools/run_private_road_ppu_321.py \
  --rom /private/game.nes --movie /private/movie.fm2 \
  --output /private/new_road_ppu321_capture \
  --timeout-seconds 1800
python3 tools/seal_private_road_ppu_321.py verify \
  --rom /private/game.nes --movie /private/movie.fm2 \
  --capture-dir /private/new_road_ppu321_capture
```

Pre- and postflight input hashes come from actual file bytes, while
FCEUX independently checks its *cartridge payload* MD5 through
`rom.gethash("md5")`. These are **different digest scopes**.
The existing older road-image numeric report lacks matching SHA-256
metadata, so this **does not verify cross-session source identity with
that road report**. An independent road capture with the same input
manifest is required before the complete Stage169 joint PPU/image
audit. This proves a private trace's integrity only, not original
NES camera motion, effective PPU raster scroll, physical collisions
or the existence of a source-quality HD remake.

Public GitHub CI uses wholly invented NES bytes, FM2 inputs and CPU
clock tables; no owner's game, FM2 or hashes are transferred.

## Stage 184 — same-session private original RGB cross-section evidence

During the **same** private FCEUX movie playback and 321-frame
CPU register trace, `emu.getscreenpixel` captures exactly four
source 256-pixel RGB scanlines at Y=120,140,160,180 on each of the
41 FM2 frames 600,608,...,920. They remain exclusively on the
owner's computer in `road_321_rgb_scanlines.bin`. A strict,
versioned 20-byte header identifies count, dimensions, and Y rows,
and each chronological record includes the exact FM2 frame index.

`tools/audit_private_road_rgb_321.py` verifies a complete,
strictly ordered 41-frame/41,984-RGB-triplet private sample. The
Stage183 input SHA-256 seal now covers **five files**, including
those private RGB pixel bytes and the 321-frame PPU writer/clock
data captured by the *same Lua callback session*.

This removes the necessity of assigning new SHA-256 hashes to
the old, hashless Stage170 numeric-only report. The new RGB source
is independently captured from the *same* verified ROM/FM2 session;
it is not a retroactive authentication of the old 37/4 report.

**The 37 accepted / four ambiguous original roadway masks have NOT
yet been re-extracted from these new RGB pixels.** The RGB acquisition
and matching input-file identity alone establish neither original
PPU effective scroll nor gameplay camera speed. A later private-only
mask analysis must independently reproduce the road edge masks
before Stage169's 37-slot join may be claimed. The raw RGB file,
checksum manifest, ROM and movie must NEVER be committed.

Public CI tests use only programmatically invented RGB channel
patterns; no copyrighted original pixels are included.
