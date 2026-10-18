# Stage123 — independent four-quadrant palette preflight

## Precondition: native Stage119–122 closure

The pinned FCEUX native job on commit `a15136afeb5a26ceb83382eb115222109c6ec1d5`
completed successfully in GitHub Actions run 39077756173. The real
synthetic Mapper-4 newppu witness reported:

- Four observed fine-scroll phases 1,3,5,7.
- Stage119 rendered XBuf color 143 for first tile, 177 for second tile
  in every phase; uniform CHR and disabled probe controls were clean.
- Stage120 matched 128 nametable-address samples and 16 tile transitions.
- Stage121 matched 128 buffered attribute-to-background-index samples.
- **No original Vice: Project Doom frame, palette or level geometry was
  observed**, and NES hardware dot timing was not established.

## Stage123 scope (separate; not another native FCEUX proof)

`tools/audit_stage123_quadrant_palette.py` creates a deterministic,
ROM-free NES palette decoding preflight. Its input attribute byte is
`0xE4`, whose 2-bit fields choose the four distinct palette groups:

| 2x2-tile quadrant | Shift | Palette group | CHR pattern=3 index | Fixture color |
|---|---:|---:|---:|---:|
| Top left | 0 | 0 | 3 | `0x30` |
| Top right | 2 | 1 | 7 | `0x31` |
| Bottom left | 4 | 2 | 11 | `0x32` |
| Bottom right | 6 | 3 | 15 | `0x33` |

For each nametable page, the preflight independently computes its
attribute address from the source tile position. The test repeats the
check across **all four logical nametable pages** with synthetic-only
address coordinates. Invalid coordinates, unknown palette indices,
mutated quadrant bytes and palette-color collisions fail closed.

The preflight excludes a zero-valued CHR pixel deliberately. Pixel zero
uses the universal backdrop color and cannot establish the distinct
palette selection asserted here.

Run the standalone tests:

```bash
python -m unittest discover -s tests -p 'test_fceux_stage123_quadrants.py' -v
python tools/audit_stage123_quadrant_palette.py
```

This is **not** a native observation of four different palette colors.
To establish that stronger claim, the next experimental ROM must write
nonidentical attribute quadrants, ensure the same nonzero CHR pattern
appears in all four, and observe the attribute read, selected palette
entry and final XBuf byte in the pinned FCEUX process. Stage123's
preflight must never substitute for those runtime checks.

No copyrighted original-game resources, memory dumps, or screenshots
are included.
