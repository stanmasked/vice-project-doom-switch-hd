# Private FM2 movie preflight (ROM-free CI)

FCEUX FM2 v3 is a timeline of controller input, **not captured graphics**.
Use tools/audit_private_fm2.py locally with a matching, privately held NES
ROM to validate the FM2 ROM checksum against PRG+CHR data. The checker does
not export ROM hashes, bytes, captured artwork, full input events or metadata
that identify a particular privately owned ROM. The supported iNES/NES 2.0 fixed-size cases reject trainers, exponent-encoded
sizes and inconsistent ROM byte counts rather than guessing.

Example local invocation:

    python3 tools/audit_private_fm2.py private/run.fm2 --rom private/game.nes --summary private/fm2_summary.json

Never commit these private inputs or outputs. The resulting windows are
**candidate checkpoints only**; a long idle may be a cutscene, pause,
dialogue, loading, credits, or menus, NOT necessarily a level boundary.
When no long pauses exist (e.g. optimized TAS play), the planner supplies
uniform checkpoints at 30-second spacing instead; those also do not prove
scene identity. A movie with port1=0 uses an empty port1 input field, not
a fabricated second gamepad. Under the official FM2 contract a movie with
no embedded savestate begins from power-on even if the first command is 0.
A matching checksum does not prove playback or completion of the final boss.

Playback is a separate step: use FCEUX in read-only FM2 mode with the exact
ROM and observe the game rendering. FCEUX's older PPU behavior and NTSC/PAL
mode should match the movie header. On a system with the emulator installed:

    fceux --playmov private/run.fm2 private/game.nes

Only after independent replay verification use the FCEUX snapshot tooling
described in REFERENCE_CAPTURE.md and PRIVATE_STAGE_CAPTURE_PREFLIGHT.md.
Keep FM2, ROM, PPU/RAM, video, and stage screenshot data strictly private.
No movie or ROM is included in GitHub tests.

Unit tests:

    python3 -m unittest discover -s tests -p test_audit_private_fm2.py -v

All sixteen tests construct invented tiny iNES/NES 2.0 and FM2 files in local temporary
directories. They never use original commercial game data. Running tests
does not establish that any uploaded FM2 reaches the game's ending.

## Verified US-region input track (private observation)

An exact locally owned US NES ROM was checked against an independently
provided US FM2 **outside GitHub**. The 43,652-frame NTSC record (~12m06s)
uses `port0=1`, `port1=0`, no initial hardware-reset command, no savestate,
and the verified ROM uses a fixed-size NES 2.0 header. The FM2 and ROM PRG+CHR
MD5 values match. The recording contains no long idle breaks suitable for
stage boundary inference; the updated input-only planner produces 25 evenly
spaced private candidate checkpoints. Authentic gameplay frames, stage
identities, victory and actual playback are **not yet confirmed**. Do not
commit the owner's ROM, FM2, hashes, capture outputs or private summaries.

## Select a specific FM2 frame window in FCEUX

The generic capture script now accepts optional `VPD_CAPTURE_START_FRAME` and
`VPD_CAPTURE_STOP_FRAME` globals, inclusive, from the aggregate FM2 plan.
When omitted, the historical full-run behavior is unchanged. Choose one
candidate window per replay; create an empty private output folder before
running the Lua script, then use FCEUX's Lua Script Window:

```lua
VPD_CAPTURE_DIRECTORY = "private/us_checkpoint_02"
VPD_CAPTURE_START_FRAME = 1736
VPD_CAPTURE_STOP_FRAME = 2496
VPD_CAPTURE_INTERVAL = 8
VPD_CAPTURE_LIMIT = 96
VPD_CAPTURE_SCREEN = false
dofile("tools/capture_fceux_ppu.lua")
```

The numbers above are a **fictional planning window derived from inputs**,
not a proven original level. The CPU-register event trace is intentionally
limited to this same selected frame window (to avoid exhausting the
250,000-event cap during a long playback). Register state before the window
is not reconstructed, so first-frame scanline scroll/CHR timing remains
unverified; use independent raster measurements before claiming geometry.
Do **not** reuse an output directory or combine two capture windows into
one audit session. The metadata records both bounds and the windowed trace
scope. A wholly fabricated Lua mock is exercised by Native Core CI, without
commercial ROMs or actual gameplay inputs.

## Window metadata cross-validation

The private preflight also verifies the optional v4 `capture_window_start`,
`capture_window_stop` and `register_log_scope` triplet. All three must
appear together and stay identical across the capture session. Every saved
frame must lie inside the declared inclusive bounds, and the only accepted
trace scope is `selected_frame_window_only`. Legacy captures without the
triplet remain accepted, but their report says
`capture_window_contract_consistent=false`. This is a structural guarantee,
not a proof of the original level or raster reconstruction. Six new
fabricated Python tests cover this contract; no private game data in CI.

On FCEUX builds exposing the older Windows-style CLI, use
`-readonly 1 -playmovie` instead; verify available switches with the exact
installed build's help first. In all cases select read-only movie playback
and keep the ROM/movie private. A Linux build may offer `--loadlua` to load
a capture script at launch; do not assume the same option exists on macOS.

## Stage 113 — one-pass FCEUX visual storyboard

The standalone `tools/capture_fceux_movie_storyboard.lua` captures the actual
FCEUX-rendered screen at fixed 1,803-frame intervals (about 30 seconds on
NES NTSC). A full 43,652-frame movie can yield 25 reference stills in **one**
private, read-only FM2 playback. This is substantially cheaper than
restarting the movie once for every capture window.

Create an empty private directory and set the following globals in FCEUX's
Lua Script Window while replaying the matching FM2 and personally held ROM:

```lua
VPD_STORYBOARD_DIRECTORY = "private/us_storyboard"
VPD_STORYBOARD_START_FRAME = 0
VPD_STORYBOARD_STOP_FRAME = 43651
VPD_STORYBOARD_INTERVAL = 1803
VPD_STORYBOARD_LIMIT = 25
dofile("tools/capture_fceux_movie_storyboard.lua")
```

Output is **private**: full-color binary P6 `.ppm` (256x240 RGB), matching
`.pal.bin` palette indices, and `.meta.txt` containing frame and FCEUX ROM
identity. The script refuses to overwrite existing captures, so use a new
empty directory per session. Convert PPM to PNG only locally if desired.
Never commit the original frames, palettes, ROM, FM2 or extracted art.

Native Core CI exercises the production storyboard Lua under fabricated
FCEUX callbacks and checks two 256x240 samples and absence of captures
outside the configured interval. This is an API/format test only: no real
playback, stage boundaries, PPU/CHR timings or map geometry are proven.

## Stage 114 — private storyboard integrity audit

Before inspecting screenshots as evidence for original stage boundaries, run:

```sh
python3 tools/audit_private_fceux_storyboard.py private/us_storyboard
```

The structural verifier checks all P6 256x240 RGB lengths/headers, per-pixel
NES palette indices, invalid-palette sentinel count, correct pairing of the
three output files per frame, FCEUX-reported ROM identity consistency, frame
order, capture cadence and selected bounds, capture limit, canonical names,
and symlink/unknown-file protection. Its report provides **only aggregate
numbers and boolean evidence limits**, never image pixels, palette bytes,
or the original ROM checksum.

A malformed session fails closed. Passing this audit means the *files agree*
with the capture metadata; it does **not** prove that the FM2 reached the
ending, that FCEUX rendered an authentic game scene, or that the reference
frames have the right stage identities. The exact Python verifier is exercised
by **16 independent ROM-free synthetic unit tests**, included in standard
Python CI discovery; these were also run locally with 16/16 success.
The new tests construct invented pixel data, not original game content.

## Stage 115 — strict complete-window verification (optional)

Use `--require-complete-window` when a storyboard is intended to cover
**all** predeclared FM2 checkpoints. The structural-only default still
accepts deliberately partial recordings, but marks
`complete_window_verified=false` and reports the expected sample count.
Strict mode regenerates the scheduled global FCEUX frame numbers from
`start_frame`, `stop_frame`, `interval` and `capture_limit` and
compares them **one by one** to the frames actually saved.

```sh
python3 tools/audit_private_fceux_storyboard.py \
  private/us_storyboard --require-complete-window
```

This is a completeness check for the **declared private window**, not
proof of the actual ROM, level boundaries, or final game completion.
Six wholly synthetic regressions cover missing start/middle/end samples,
non-aligned starts, capture limits and default opt-in behavior.
22 storyboard Python tests now pass locally; GitHub Actions remain
a separate exact-commit verification.

## Stage 115 — verified completeness and private PNG contact sheet

When the full American FM2 has actually finished in FCEUX, first run the
storyboard audit in strict mode. Unlike the historical integrity-only
preflight, strict mode rejects missing scheduled frames in an otherwise
well-formed partial capture:

```sh
python3 tools/audit_private_fceux_storyboard.py private/us_storyboard \
  --require-complete-window
```

Then create a **private** 5-column PNG with embedded frame-number captions:

```sh
python3 tools/build_private_fceux_contact_sheet.py \
  private/us_storyboard private/us_contact_sheet.png --columns 5
```

The source frame schedule for the intended run is 0 through 43,651
(inclusive), interval 1,803 and maximum 25 samples. A full uninterrupted
movie playback should therefore yield 25 candidate stills, displayed in
a single 1280×1280 PNG (5 columns × 5 rows, each 256×240 plus a 16-pixel
frame-number banner). These are **visual reference checkpoints**, NOT
verified level boundaries or full gameplay recovery.

The contact-sheet tool requires a complete audited window by default,
refuses overwrites, and writes the PNG **outside the strict source folder**
so it cannot contaminate later audits. For investigating an interrupted
capture only, `--allow-partial` explicitly opts out of the completion
requirement. Do not publish source game images or the contact sheet.

Python stdlib only (no Pillow dependency). Six wholly fabricated regression
tests validate PNG dimensions, source pixel placement, strict/partial
handling, output directory isolation and overwrite protection. Local Python
tests: 22 storyboard integrity + 6 contact-sheet = **28/28 PASS**.
Latest GitHub Actions is a separate verification and may still be queued.

## Stage 122 — CPU-confirmed controller input in real FCEUX

The synthetic, run-only NROM 6502 program now polls controller A through
`$4016` and stores the hardware bit in invented zero-page `$0000`. The
fabricated 64-frame FM2 presses A on frames 12–23. The live FCEUX Lua
callback must observe `$0000 = 0` on frame 8 and `$0000 = 1` on frame 16,
while the movie stays read-only in playback mode. The CI witness must contain
both results and an explicit CPU controller-provenance field; the separate
storyboard frames remain subject to strict audit. This verifies playback
input effects on an invented NES CPU program, not original Vice: Project Doom
input, scene geometry, or movie synchronization. Original ROM/FM2 never
enter GitHub Actions. Recheck exact-head CI before treating this as proven.


## Stage 123 — privately run the complete verified FM2 (source-only, no upload)

A new **opt-in private executable** now connects the working FCEUX Lua
capture pipeline to an actual matching local NES+FM2 pair without uploading
either. Example (Linux FCEUX 2.6.5, in a local environment containing
privately owned game files):

    python3 tools/run_private_fm2_storyboard.py \
      --rom "/private/Vice Project Doom.nes" \
      --movie "/private/taotao-viceprojectdoom.fm2" \
      --output "/private/us_capture_001"

The runner first verifies the complete FM2 format and ROM PRG+CHR checksum,
rejects untrusted initial states and existing output paths, and will refuse
to write captures inside any Git checkout. It then launches local FCEUX
with the actual private ROM and read-only FM2, keeping screen images, palette
values, logs and witness under user-chosen private directories. Every run
uses 1,803-frame checkpoints and a maximum of 64 samples, producing 25
expected stills for the previously verified 43,652-frame American movie.

The **Lua terminal witness** verifies sustained read-only playback and the
last requested frame number. Only a witness and a complete strict Python
capture audit allow the runner to claim the *terminal movie timeline* was
observed. This is NOT evidence that every original gameplay scene rendered
correctly, no gameplay desynchronization occurred, or that the final boss
was defeated: those require independent frame-by-frame source inspection.
If a capture fails or is interrupted, nothing is reported as a passing
full private replay. Running the program is entirely local and never
performed by GitHub Actions on the private ROM.

Only this general-purpose source code and 7 fabricated planning/guard tests
are checked into GitHub. The real FCEUX environment available in CI was
confirmed earlier with a different invented NES+FM2. The new private runner
has **not** been run against the owner's original game here because an
installed local FCEUX binary is unavailable.

Stage 123 capture-cadence correction: FCEUX may attach Lua after frame 0.
The private full-run script therefore begins snapshot sampling at the
**first positive frame divisible by the interval** instead of assuming
frame 0 can be observed. For 43,652 US FM2 frames and interval 1,803, this
means 24 guaranteed-scheduled images (frames 1,803 through 43,272), not
25. The terminal movie witness still requires the last FM2 frame 43,651.


## Stage 125 — privacy-preserving candidate-scene analysis

After a real private FCEUX full-playback run has produced a strictly
audited storyboard, invoke the new Python visual-change tool:

    python3 tools/audit_private_fceux_visual_changes.py /private/us_capture_001

The tool first runs the existing complete-window integrity verifier.
It compares sampled screen palette indices and their distributions
between adjacent screenshots, recording only frame numbers and numerical
change ratios when both independent thresholds are exceeded. An excessive
number of unavailable palette (254) samples suppresses rather than fabricates
a visual-change conclusion. The tool exports no images, sprite pixels,
tile patterns, ROM checksums, raw palettes or proprietary game assets.

A candidate means only that two sparse screenshots appear visually different.
It does NOT prove a level boundary, boss scene, clear, or game completion.
Transitions between 1,803-frame checkpoints are not fully observed.
Final identification requires additional private gameplay and PPU/RAM evidence.

Use --allow-partial only to investigate interrupted sessions; those outputs
explicitly report complete_window_verified=false. Defaults are stride 4,
pixel threshold 0.55, and palette threshold 0.35. Never put original
screenshots, palette dumps or extracted game art into GitHub.

Nine independent ROM-free tests exercise invented normal, shifted,
unavailable, corrupted, incomplete, and partial screenshots.

## Stage 126 — private US/Japan cartridge-bank comparison

Use `tools/audit_private_nes_variant_banks.py --first-rom /private/us.nes
--second-rom /private/jp.nes` to compare privately held FCEUX sources.
This scanner requires equal Mapper and PRG/CHR sizes, but accepts an NES 2.0
header on one version and classic iNES on the other. It compares 1KB
cartridge banks at identical offsets and emits only bank numbers plus
numeric difference counts, never source bytes, original tile graphics,
original CPU instructions, nor ROM/FCEUX asset digests.

Verified privately for the owner's US Vice Project Doom and Japanese
Gun-Dec (262,160 bytes each, mapper 4 / MMC3): all 128 KB PRG + 128 KB
CHR are size-aligned across versions. 125/128 one-KB CHR banks were
identical at their original positions. The three differing CHR banks
are 124, 125, and 126 (929, 898, and 571 differing bytes).
87/128 PRG banks were identical at equal offsets, so gameplay equivalence
and level order are **not** proven and must not be inferred from CHR alone.

Nine ROM-free, entirely invented fixtures test header variants, aligned
bank comparisons and fail-closed behavior on incompatible layouts, linked
files and malformed inputs. No actual commercial ROM is used by CI.
Original cartridge images and the private audit report are not committed.

### Private CHR difference atlas (Stage 126)

If inspection is authorized on a local copy of both ROM variants, produce
an exact grayscale 2-bit planar CHR **pattern** comparison with:

    python3 tools/render_private_nes_variant_chr_diff.py \
      --first-rom /private/vice_us.nes --second-rom /private/gun_dec_jp.nes \
      --private-output /private/chr_differences.png

This draws only nonidentical 1KB CHR banks, preserving the original
NES bitplane arrangement. The tones are invented visualization colors:
without PPU palette/attribute/scroll evidence, the resulting tiles
cannot be called in-game screen frames, backgrounds or stage geometry.
Never upload the resulting proprietary-pattern image to GitHub.
Output is refused inside any Git checkout, if an image already exists,
or if more than 16 differing banks would exceed the comparison layout.
Eight wholly invented ROM-free tests exercise rendering and guards.


## Stage 127 — per-tile CHR origin and reuse audit

The source-only `tools/audit_private_nes_variant_chr_tiles.py` computes
precise 16-byte planar 8x8 tile identities between two privately owned
NES cartridges. In addition to the same-index tile changes, it counts
changed tile patterns that are completely absent in the other ROM's
entire CHR. This distinguishes a genuinely novel static tile pattern
from an unchanged/reordered pattern copied elsewhere. For each changed
1KiB bank it reports changed global tile indices and the number of
all-zero tiles on each side.

Example: python3 tools/audit_private_nes_variant_chr_tiles.py
  --first-rom /private/vice_us.nes --second-rom /private/gun_dec_jp.nes

Never upload original ROMs or optional private reports to public CI.
All output fields are numeric provenance plus explicit `false` evidence
limits; no raw graphics, patterns, hashes, image pixels, or game art.
The analysis does not determine CHR selection timing, PPU compositing,
screen coordinates, text semantics, level order or gameplay mechanics.

Seven tests synthesize original-made 8x8 patterns, bank shifts, zero
tiles, mapper incompatibility and comparison bounds. A real emulator
capture is still required to link a static pattern to an original stage.


## Stage 128 — real FCEUX NES 2.0 MMC3 (Mapper 4) compatibility gate

Previous real-FCEUX smoke tests used a wholly invented iNES Mapper 0 game.
The owner's original American cartridge instead has 128 KiB PRG,
128 KiB CHR, NES 2.0 header and Mapper 4 (MMC3). A new exact-layout
**wholly original 6502 program** is generated transiently inside GitHub
Actions by tools/build_fceux_smoke_mmc3_nes2.py. Only the standard header
and CPU/controller protocol are comparable; this never substitutes
commercial program code, graphics, stage resources, or original FM2 inputs.

The generated FM2 is accepted only if its source ROM bytes match one of
two explicitly handcrafted synthetic fixtures (NROM or MMC3). Real FCEUX
must load the MMC3 synthetic ROM and play that movie read-only, witness
controller A released at frame 8 and pressed at frame 16 from actual
CPU reads of $4016 to RAM, produce strict frame 8 and 16 captures,
then pass the generic full-timeline runner to terminal frame 63 with
all seven planned 8-frame snapshots. A passing test confirms FCEUX
MMC3/NES2 wiring but **not** the original game's movie synchronization.

No owner's ROM, FM2, extracted CHR or original screens enter public CI.
At this stage the user-owned American FM2 still requires private replay.


## Stage 129 — MMC3 mapping-write candidate audit (not PPU rendering proof)

After a private FCEUX PPU capture produces `mmc3_video_writes.tsv`, run:

    python3 tools/audit_private_mmc3_chr_mapping.py \
      /private/capture/mmc3_video_writes.tsv \
      --private-rom /private/ViceProjectDoom.nes \
      --target-banks 124,125,126 --frame-interval 1803

Uses existing fail-closed strict `video_events` parser to reconstruct
MMC3 $8000 selection and subsequent $8001 data for CHR R0..R5.
R0/R1 map a 2KiB pair (low bit ignored); R2..R5 map single 1KiB
bank; inversion mode is counted. Report includes only numeric mapped
bank candidates and frame intervals. No raw trace, original ROM hash,
tile bytes, sprites or artwork are serialized.

A *mapper register selection* is NOT proof the corresponding CHR data
was fetched by PPU or visible in a rendered frame. Separate original
gameplay and PPU data are necessary. Twelve synthetic tests include
non-CHR register exclusion, unresolved data writes, pairing, inversion,
out-of-order events, invalid headers, and linked-file rejection.

## Stage 130 — opt-in private FM2 mapper-write timeline

Use `--trace-chr-banks 124,125,126` with `tools/run_private_fm2_storyboard.py` to register only bounded CHR-related MMC3 `$8000/$8001` pairs while replaying an owner-held local ROM and FM2. The Lua handler deduplicates register+data selections within each capture interval; its private TSV is written outside the strict storyboard directory and analyzed by `audit_private_mmc3_chr_mapping.py`. The emitted report contains only selected bank numbers, counts, candidate intervals and explicit false provenance flags for PPU rendering and level identity. No proprietary bytes or original captures enter public CI.

The invented NES2 Mapper 4 smoke cartridge now performs R0=125 (effective banks 124/125) and R2=126 writes in its CPU loop; the real FCEUX workflow uses the full private-style runner with the tracing option and checks that all three mapping targets were actually observed. This proves mapper register writes reached the emulator, *not* that any corresponding sprites were rendered or that the owner's real FM2 completed.
