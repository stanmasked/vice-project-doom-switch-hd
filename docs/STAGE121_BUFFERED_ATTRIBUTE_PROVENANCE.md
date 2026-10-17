# Stage121 — native PPU attribute fetch to buffered pixel index

## New evidence over Stage119–120

The earlier synthetic Mapper-4 tests connect nametable tile ID, its
actual fetch address, both CHR planes, and the rendered XBuf byte.
Stage120 checks per-tile nametable address increments relative to an
**observed row origin**, rather than incorrectly fixing it to $2000.

Stage121 instruments three points in the pinned upstream FCEUX
`BGData::Record::Read()` and the existing rendered pixel site:

1. The actual `RefreshAddr` used for the attribute-byte PPU read.
2. The byte returned by `CALL_PPUREAD(RefreshAddr)` plus the
   actual `ppur.vt/ppur.ht` quadrant selector before mutation.
3. The buffered palette select `bgdata.main[bgtile].at` and the
   actual combined background pixel index, not a value reconstructed
   from the XBuf color.

For a source nametable address `nt`, the independent attribute-address
check uses:

```text
attribute_address = $23C0 + (nt & $0C00)
                    + ((nt & $0380) >> 4)
                    + ((nt & $001C) >> 2)

shift = (nt & $0040 ? 4 : 0) + (nt & $0002 ? 2 : 0)
palette_bits = ((raw_attribute >> shift) & 3) << 2
background_index = (chr_pattern & 3) | palette_bits
```

The native check rejects mismatched table-page aliases, wrong
quadrant selection, bad raw attribute bytes, incorrect buffered palette
bits and a combined pixel index inconsistent with the observed pattern.

## Scope and negative controls

Only the existing generated Stage119 ROMs are eligible. Their synthetic
PPU initialization writes alternating 0/1 throughout $2000–$2FFF,
including attribute bytes. The observed byte range 0..1 is checked,
but these ROMs **do not yet exercise all four distinct attribute
quadrants or demonstrate four different palette colors**. A subsequent
experiment needs a custom attribute pattern and populated palette RAM
to prove chromatic selection, without disturbing existing Stage119
controls.

The native observer processes 16 pixels in each of two known rows
and requires the full 4-phase fine-X sweep, amounting to 128
sampled background indices. The independently compiled C++ regression
mutates only a fetched attribute address to its +$0400 alias.
Stages119–120 must still pass, while Stage121 rejects the false origin.

The run produces a single Stage121 PASS or REJECTED marker per native
process; the strict Python audit binds its addresses to **both**
Stage119 and Stage120 results. It is mandatory in the existing
pinned-FCEUX pipeline and is also exercised separately in Python
and C++11 unit tests.

```bash
python -m unittest discover -s tests -p 'test_fceux_stage121_attributes.py' -v
```

A passing test fixture alone cannot establish that the pinned native
FCEUX build succeeds. Nothing here establishes original Vice: Project
Doom palettes, actual game raster composition, NES hardware cycle
timing, original sprites or a running Switch HD remake. No ROMs,
original screenshots, captured tile bytes or original-game art
are included in the public repository.
