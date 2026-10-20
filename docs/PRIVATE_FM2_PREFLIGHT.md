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

    fceux -readonly 1 -playmovie private/run.fm2 private/game.nes

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
