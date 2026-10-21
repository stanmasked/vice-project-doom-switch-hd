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
