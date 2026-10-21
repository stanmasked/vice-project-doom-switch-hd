# Stage 32 — Evidence-gated first-stage tile observation

**Status:** Tooling verified with invented captures; a genuine first-stage
map has NOT been recovered. No real FCEUX gameplay recordings are available
in the repository or this diagnostic environment.

The local original ROM has an NES header indicating MMC3 mapper 4 with
128 KiB PRG and 128 KiB CHR. Static video analysis identifies PPU/CHR
register paths, but this does not identify actual world geometry.

## What the stitcher does

[stitch_stage_captures.py](../tools/stitch_stage_captures.py) samples
8x8-pixel tile IDs and two-bit attribute palette assignments from
captured PPU nametables. It maps them to **world tile coordinates**
using camera and PPUSCROLL offsets supplied separately by the researcher.

Every output cell has a count and all capture sources. Repeated matching
observations are recorded as agreement. Different tile/palette observations
at the same world coordinate are kept as explicit **conflicts**; the
tool does not guess a majority or invent a collision tile.

These PPU observations are *hypotheses about nametable memory state*,
not a visual-screen reconstruction: postframe PPU memory may differ from
the picture rendered during the scanline due to MMC3 IRQ, CHR switching,
HUD scroll splits, sprites, and game objects. A tile index is never
proof of a solid collision cell or metatile ID.

## Required local inputs

Before providing externally measured camera/scroll values, run the
[ROM-private capture preflight](PRIVATE_STAGE_CAPTURE_PREFLIGHT.md) on the
local FCEUX capture directory. It rejects truncated or inconsistent
PPU/RAM/screen files and missing FCEUX metadata, but it **does not**
authenticate that gameplay was really recorded or infer the world
camera from RAM values. A clean file-integrity result is a prerequisite
for measurement, not evidence of restored original geometry.


Use [capture_fceux_ppu.lua](../tools/capture_fceux_ppu.lua) to obtain
private frame_NNNNNN.ppu.bin and frame_NNNNNN.meta.txt snapshots from
the user's lawfully obtained ROM during the actual first stage.

The manifest must name at least one capture and contain:

- Captured frame, relative prefix and ROM MD5 as reported by **FCEUX**.
- Measured camera X/Y and documented sources for these values.
- Measured PPUSCROLL X/Y, initial nametable, and documentation of the
  measurement source (e.g., CPU-cycle PPU port trace with raster analysis).
- Explicit scanline interval to exclude status bar and other screen splits.

The tool rejects incomplete/unknown register logging by default, and
refuses camera-versus-scroll positions with incompatible tile-grid phase.
An override can permit incomplete logging but clearly labels this
weakness in its report; it never upgrades confidence to verified.

Example manifest, **all numerical values are fictional**:

~~~json
{
  "schema": 1,
  "rom_md5": "ffffffffffffffffffffffffffffffff",
  "captures": [{
    "prefix": "frame_000240",
    "frame": 240,
    "camera_x": 0,
    "camera_y": 0,
    "scroll_x": 0,
    "scroll_y": 0,
    "nametable": 0,
    "screen_y_start": 32,
    "screen_y_end": 208,
    "camera_source": "Independently measured camera state",
    "scroll_source": "Measured effective PPUSCROLL after raster analysis"
  }]
}
~~~

**Do not use these sample coordinates as actual Vice: Project Doom data.**
Especially do not infer that `scroll_x == camera_x`, that Y=0, or that
the entire screen shares the same PPU scroll. Those remain to be measured.
The ROM MD5 in the manifest must match FCEUX `rom.gethash('md5')` from
the metadata; it need not be identical to an MD5 of the complete `.nes`
file including its header. Use the value observed in capture metadata.

Keep the manifest and captures under a Git-ignored private directory:

~~~sh
python3 tools/stitch_stage_captures.py private/first_stage/manifest.json \
  --out private/first_stage/tile_observations.json
~~~

Report fields include `sampled_world_tiles`, `repeated_world_tiles`,
`conflicting_world_tiles`, `agreed_tile_id`, `agreed_attribute_palette`,
and per-candidate source frame/prefix. **Never commit** original-game
snapshots, stitched map output, palette data, or screenshots.

## Automatic validation

Five ROM-free synthetic tests cover 2x2 nametable crossings and attributes,
two overlapping camera positions, explicit multi-candidate conflicts,
invalid metadata/ROM identity, incomplete capture logs and phase disagreement.

Run:

~~~sh
python3 -m unittest discover -s tests -p test_stitch_stage_captures.py -v
~~~

## What is still missing

1. A verified real FCEUX capture **during the first playable stage**.
2. Measurement of effective camera and scroll positions, including HUD splits.
3. Repeated captures with overlap so conflicting game-state changes can be
   distinguished from actual spatially stable nametable tiles.
4. Separate reverse engineering of first-stage collision metatiles, entity
   positions/events, player movement and native scene matching.
5. Actual Switch hardware video/performance validation.

Until those measurements exist, the project has **no trustworthy original
first-stage map**. All currently rendered native stage layouts are still
independently authored prototypes.

## Dense capture mode for scrolling stages

The FCEUX Lua script now allows **opt-in** sample cadence and count.
Set these globals in FCEUX **before** executing the script:

~~~lua
VPD_CAPTURE_DIRECTORY = "private/first_stage"
VPD_CAPTURE_INTERVAL = 8
VPD_CAPTURE_LIMIT = 96
VPD_CAPTURE_SCREEN = false
dofile("tools/capture_fceux_ppu.lua")
~~~

The example values are **suggested acquisition settings**, not
measured frame timings of the original game. The optional
`VPD_CAPTURE_SCREEN=false` avoids expensive per-pixel screen capture;
keep screen references enabled when validating actual rendered output.

Defaults remain every 120 frames / maximum 24 files, for backwards
compatibility. Accepted ranges are 1–1200 for interval and 1–512 for
count. Metadata contains `capture_interval` and `capture_limit`.
The native CI mock verifies default and 8-frame dense acquisition, but
this is **not** a successful real FCEUX gameplay recording.
