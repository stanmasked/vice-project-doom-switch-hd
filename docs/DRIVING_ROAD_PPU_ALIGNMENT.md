# Stage 168 — Joint original road-image and PPU-writer observations

Paired numeric evidence from the prior private FCEUX runs documented in
[the stage transition contract](ORIGINAL_STAGE_TRANSITION_CONTRACT.md)
and [Stage 167](DRIVING_ROAD_IMAGE_REFERENCE.md).

| Zero-based original FM2 frame | Second written $2005 value | End-of-frame RAM $0D | Approx. visible road width | Approx. image center |
|---:|---:|---:|---:|---:|
| 600 | 79 | 79 | 123 | 127.0 |
| 744 | 136 | 134 | 123 | 127.0 |
| 800 | 144 | 139 | 56 | 127.5 |
| 920 | 24 | 19 | 88 | 159.5 |

These are matched movie-frame labels for two independent *observations*,
not a fitted model of gameplay physics or display-effective scroll.

The prior original FCEUX callbacks cover 321 frames (600–920) and
1,284 writes to $2005. Each original frame exhibited the executed
writer-PC order `$E8EC, $E8F1, $E369, $E36C`, with written value order
`00, changing, 00, 00`. The first two writes were 7 CPU cycles apart,
and the late two were 4 cycles apart. The executed original `LDA $2002`
instruction at $E8E7 is *not* a directly captured PPUSTATUS bus-read.

End-of-frame $0D differs from the earlier register's written value
at frames 744, 800 and 920, so postframe RAM must not be treated as
the exact earlier emitted register value. Frames 600 and 744 share the
same *visible image-space* width (123 pixels) despite very different
written source values (79 and 136). This does **not** prove causality
or rule out a more complex original rendering model.

The new `game_core/driving_road_ppu_alignment.hpp` and C++ test only
join the four explicitly reported labels, reject unobserved movie
frames, and verify source writer PC provenance, counts and timing.
All actual original CPU traces, ROM, FM2, sprites and RGB files remain
owner-private. The observed PPU scanline/dot, effective display scroll,
road collision mesh, and camera speed remain **unverified**.
