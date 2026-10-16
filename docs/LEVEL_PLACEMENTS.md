# Stage 31 — Data-driven decoration placements (VLAY v1)

The native Switch raster diagnostic now reads independently authored world
object placements instead of hardcoding prop positions in C++.
All positions are synthetic. They are NOT original Vice: Project Doom level data.

## Authoring

Edit assets/demo_decor_layout.json. Objects are JSON records with these fields:

- x, y: signed world coordinates in logical pixels.
- kind: beacon or fan; an authoring label, not collision logic.
- layer: rear (behind terrain/hero) or front (before HUD, after hero).
- first_frame: index of the first frame in decor.vpat (0..3).
- frames: consecutive frame count (1..4), within the 4-frame atlas.
- period_ticks: game simulation ticks per frame (1..600).
- phase_frames: phase offset in animation frames (0..65535).

Create a replacement SD binary:

    python3 tools/pack_decor_layout.py private/layout.json --binary private/decor_layout.vlay

Generate embedded C++ declarations from a JSON document:

    python3 tools/pack_decor_layout.py assets/demo_decor_layout.json --header private/layout.hpp

Zero external objects is valid and hides all decorations.
The embedded default is required to contain at least one placement.

## VLAY v1 binary format

All multi-byte values are little endian. The 16-byte header contains:

| Offset | Type | Description |
|---:|---|---|
| 0 | ASCII[4] | VLAY |
| 4 | u16 | Version 1 |
| 6 | u16 | Object count 0..64 |
| 8 | u16 | Record size 12 |
| 10 | u16 | Flags 0 |
| 12 | u32 | CRC32 of bytes from offset 16 onward |

Each record is 12 bytes:

| Offset | Type | Description |
|---:|---|---|
| 0 | i16 | World X (-16384..16384) |
| 2 | i16 | World Y (-1024..1024) |
| 4 | u8 | Kind: 0 beacon, 1 fan |
| 5 | u8 | Layer: 0 rear, 1 front |
| 6 | u8 | First frame |
| 7 | u8 | Number of frames |
| 8 | u16 | Period ticks |
| 10 | u16 | Phase frames |

Maximum file size: 784 bytes, for 64 objects. Every record is validated
before the active placement array can change; invalid files preserve the
previously loaded layout. CRC32 detects accidental corruption, not tampering.

## Switch SD layout and controls

Put the file at:

    sdmc:/switch/vice_project_doom/decor_layout.vlay

Controls:

| Input | Action |
|---|---|
| Minus | Reload decoration placements (VLAY) |
| Right-stick press (R3) | Restore built-in placements |
| D-pad Up / Down | Reload/reset decorative pixel atlas |
| L / R | Background layers |
| ZL / ZR | Terrain atlas |
| X / Y | Hero and animation assets |
| Plus | Exit |

An on-screen label shows LAYOUT: SD, LAYOUT: EMBEDDED, or LAYOUT: FAILED.
The external layout is independent of decor.vpat. It is validated against
the current fixed 4-frame decoration atlas contract.

## Projection and animation

screen_x = (world_x - camera_x) * 2
screen_y = (world_y + 80) * 2
frame = first_frame + ((tick / period_ticks + phase_frames) % frames)

The +80 camera-Y origin and all object positions are authored test values.
Decoration objects do not change collisions, enemy AI, physics or map topology.

## Validation

Portable C++ and Python regressions exercise schema bounds, different
positions/timings, frame clipping, camera scroll, CRC failures, empty
scenes, rejected corrupt files and last-good rollback.
GitHub Actions compiles the same implementation into a native libnx NRO.

Neither real first-stage placements nor authentic animations are recovered.
Physical Nintendo Switch runtime and performance remain unverified.
