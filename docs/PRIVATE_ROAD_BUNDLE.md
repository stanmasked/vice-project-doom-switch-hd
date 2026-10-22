# Stage 176 — validated private 37-frame road bundle

The original owner-private numeric-only FCEUX road-mask report has
41 movie-frame slots from 600 through 920 at an 8-frame cadence.
37 are accepted, 4 are explicitly ambiguous (712,720,728,736).
The legacy report does **not** include independent original ROM/FM2
SHA-256 hashes. It is a source RGB road-color **observation**, not a
road collision map, original PPU scroll, NES camera velocity or mesh.

Use `tools/pack_private_road_bundle.py` on a *private* computer with
your existing, already-audited numeric JSON. No input or output
belongs in GitHub:

```bash
python3 tools/pack_private_road_bundle.py \
  --numeric-report /private/road_geometry_600_920.json \
  --output /private/sdmc/switch/vice_project_doom/road_numeric.vprd
```

The CLI refuses output paths inside this public source checkout.
Its 164-byte `VPDROAD1` record consists of the 8-byte magic, 16-bit
LE version 1, 16-bit LE sample count 37, CRC32 of the payload and 37
ordered little-endian `{frame:u16,left:u8,right:u8}` records.

`game_core/driving_road_private_bundle.hpp` parses and validates the
same format, checking file length, checksum, order, exact permitted
frames, published seven source anchors, ranges, omission of ambiguous
frames and an absence of extrapolation. No dynamic allocations, game
sprites, ROM bytes or private source images are included. Invalid
bytes must clear any previously loaded observations and cannot
activate a display. Missing SD file is a clean optional outcome.

**Scope:** This step delivers the private packer and native-safe loader
only. It does **not yet wire the loader to the running NRO**; the seven
already confirmed review frames remain the available Switch view
until a separate manual-only full-data selector is implemented and
verified. Tests use invented numeric fixtures exclusively.
