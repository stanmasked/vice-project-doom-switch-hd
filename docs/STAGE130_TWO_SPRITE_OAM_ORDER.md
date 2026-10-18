# Stage130 — independent two-sprite OAM arbitration model

Stage129 confirmed real OAM sprite0 rendering, background priority and
sprite-0 hit in the pinned FCEUX `newppu` renderer (GitHub Actions
39083884272). Stage130 examines **two overlapping sprites**. It adds
a separate **source-level** audit and independent Python model. It does
**not** yet claim that two sprites were observed simultaneously in the
native FCEUX framebuffer.

The earlier OAM-indexed sprite producing a nonzero CHR pixel sets
`havepixel` **before** testing whether its priority is behind opaque
background. Consequently a later front-facing sprite cannot appear
through the first sprite even when that first sprite itself is hidden
behind the background. Conversely, a transparent sprite does not claim
the pixel, allowing the next opaque sprite to render.

Sprite-0 hit is independent from the visible winner.

| OAM0 / OAM1 | Background | Expected XBuf | Sprite-0 hit |
|---|---|---:|---|
| Solid palette0 / solid palette1 | Opaque | First sprite, 170 | Yes |
| Solid palette1 / solid palette0 | Opaque | First sprite, 184 | Yes |
| Transparent / solid palette1 | Opaque | Second sprite, 184 | No |
| Solid behind / solid front | Opaque | Background, 176 | Yes |
| Solid behind / solid front | Transparent | First sprite, 170 | No |
| Sprites disabled | Opaque | Background, 176 | No |

The reference model accepts exactly two validated sprite records
with OAM indices 0 and 1, CHR values 0–3, palette groups 0–3,
explicit pixel position and boolean priority/visibility values.
Six regression tests exercise the table, source-guard mutation cases,
and invalid argument controls.

The source audit requires the pinned FCEUX `ppu.cpp` and checks
`for (s ...)`, `havepixel` rejection, transparent-pixel skip,
sprite-0 hit, setting `havepixel`, behind-background priority,
and final sprite-palette selection **in their exact order**.

```bash
python -m unittest discover -s tests -p 'test_fceux_stage130_two_sprite_order.py' -v
python tools/audit_stage130_two_sprite_order.py /path/to/pinned/fceux/src/ppu.cpp
```

The full native CI runs the source audit before instrumenting FCEUX.
Successful unit tests or this source audit must not be described as
native dual-sprite pixel evidence. That stronger proof requires a new
synthetic ROM with two overlapping OAM entries, independently
distinguishable sprite CHR and palette colors, and actual XBuf samples
plus negative controls.

No original *Vice: Project Doom* ROM, enemy, character art or
framebuffer memory is placed in the public repository.
