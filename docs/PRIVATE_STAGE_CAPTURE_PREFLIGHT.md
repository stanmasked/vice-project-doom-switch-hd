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

All **19 Python tests** fabricate private captures in temporary
directories. No NES images, copyright artwork or original-game ROM
identity is stored in this repository.
