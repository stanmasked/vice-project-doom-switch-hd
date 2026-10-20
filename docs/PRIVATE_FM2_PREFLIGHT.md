# Private FM2 movie preflight (ROM-free CI)

FCEUX FM2 v3 is a timeline of controller input, **not captured graphics**.
Use tools/audit_private_fm2.py locally with a matching, privately held NES
ROM to validate the FM2 ROM checksum against PRG+CHR data. The checker does
not export ROM hashes, bytes, captured artwork, full input events or metadata
that identify a particular privately owned ROM. The supported iNES case
excludes trainers, NES2 and noncanonical ROM byte counts rather than guessing.

Example local invocation:

    python3 tools/audit_private_fm2.py private/run.fm2 --rom private/game.nes --summary private/fm2_summary.json

Never commit these private inputs or outputs. The resulting windows are
**input-resumption candidates only**; a long idle may be a cutscene, pause,
dialogue, loading, credits, or menus, NOT necessarily a level boundary.
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

All ten tests construct invented tiny iNES and FM2 files in local temporary
directories. They never use original commercial game data. Running tests
does not establish that any uploaded FM2 reaches the game's ending.
