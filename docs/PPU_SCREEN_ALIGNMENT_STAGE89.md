# Stage 89 — reference-screen matching with explicit uncertainty

## Goal

Before creating any geometry or HD artwork, compare the **saved,
byte-verified FCEUX palette-index screen** with the **static
reconstructions** from the corresponding byte-verified PPU snapshot.
This can rank small diagnostic hypotheses; it must never be
misrepresented as reconstructing the first level or reproducing the
NES's true raster timing.

The new tool is `tools/audit_ppu_screen_alignment.py`. It can operate
only on a finalized local session that passes the independent
`verify_ppu_capture_session.py` gate from stages 79–87.

## Usage (original assets remain local)

```bash
python3 tools/audit_ppu_screen_alignment.py \
  private/ppu_capture_session.meta.txt \
  --require-cycle --require-screen \
  --out private/ppu_screen_alignment.json
```

The optional `--require-cycle` flag refuses an unclocked capture;
`--require-screen` refuses a session with no saved emulator screen.
The report is **JSON with numeric aggregates only**. The program
does not save raw pixels, graphics, palettes, CHR patterns or
reconstructed images.

The repository is **public**. Original ROMs, FCEUX captures, screenshots,
derived graphic previews and local alignment reports should remain
outside GitHub under ignored `private/`.

## Provenance tiers

Each captured frame has one of two explicit states:

- `verified_screen_file`: the entire session, both TSV logs (when
  present), the PPU/RAM snapshot and FCEUX RGB/palette screen files
  have passed checksum and structural verification
- `not_captured`: no reference image was saved; **no** comparison
  or inferred screen image is produced

The tool tests up to eight tightly controlled static background
hypotheses per referenced frame: four nametable address windows
times one background pattern table (if the snapshot's PPUCTRL is
known) or **both** tables (if PPUCTRL is unknown). The static
renderer uses **assumed zero scroll**, the observed PPUMASK when
present, and **no sprite overlay**. It does not optimize scroll,
texture banks or timing to artificially fit the reference.

The numerical report records, for each hypothesis, comparable,
matching and differing pixels, omitted reference pixels marked
`254`, and a mismatch fraction when at least one reference pixel
can be compared. The lowest-error candidate is named
`lowest_error_hypothesis`, **not** authentic layout. Tied
hypotheses are counted; if all reference pixels are unknown there
is no winner.

Every frame includes a provenance classification that distinguishes
the byte-verified observation from assumptions about nametable
selection, zero scroll, mid-frame CHR switching and missing sprites.
The entire report explicitly declares:

```text
physical_frame_boundaries_proven = false
actual_scroll_proven = false
chr_midframe_mapping_proven = false
sprites_reconstructed = false
first_level_identity_proven = false
level_geometry_reconstructed = false
```

Even a **0% mismatch** under one static hypothesis is not
authentication of the original game's visual geometry: nametable
mirroring, changing IRQ banks, actual scroll, sprite content,
emphasis and raster timing remain unresolved.

## Regression verification

Seven new synthetic cases in `tests/test_ppu_capture_session.py`
verify candidate enumeration, PPUCTRL-known and -unknown
alternatives, omitted `254` reference pixels, absent references,
uniformly unknown images, checksum rejection after one-byte
damage, and private-output minimization. The fixture uses only
fabricated binary data and checks the **real strict session validator**
before any comparison.

The GitHub `Native Core CI` executes the Python and Lua regression
suites, C++ unit tests and tracked-artifact policy. A passing
synthetic CI is not live FCEUX gameplay evidence.

## Next evidence needed

Obtain an authentic first-level FCEUX capture **locally**, including
the emulator's screen reference and a trace whose identity is
separately authenticated. Compare ranked static background
hypotheses, inspect disagreements, and add trusted scroll/CHR/OAM
observations before any attempt to reconstruct level geometry.
