# Stage 88 — verified PPU reference-frame inventory

## Goal and current evidence boundary

The next useful graphics-research step is to evaluate whether a **single
complete local FCEUX session** contains enough distinct, trustworthy
PPU/RAM samples to justify manual investigation of background graphics.
The existing `compare_ppu_captures.py` compares only two snapshots;
`render_ppu_snapshot.py` produces an individual *static* background
preview, not the NES's actual raster output.

This stage adds `tools/audit_ppu_reference_frames.py`, a **ROM-free
session-wide inventory**. It does not fabricate the first-stage level
map, identify the scene, infer camera motion or redistribute graphics.

## How to run (owner's local machine)

First run `tools/capture_fceux_ppu.lua` with the owner's authorized
copy of the game in FCEUX and save its outputs in ignored `private/`.
Close the emulator normally to produce the finalized
`ppu_capture_session.meta.txt`. If the capture is incomplete or
crashes, the report intentionally refuses it.

```bash
python3 tools/audit_ppu_reference_frames.py \
  private/ppu_capture_session.meta.txt \
  --require-cycle \
  --out private/ppu_reference_inventory.json
```

The `--require-cycle` switch is optional and prevents an unclocked
capture from being inadvertently used in CPU-cycle analysis. It does
not grant proof of exact PPU timing even when the clock trace exists.

**Keep the JSON in `private/`** with the screenshots, raw PPU dumps
and RAM. The repository is now public: do not upload or commit an
original NES ROM, game-derived artwork, screenshots, private emulator
captures or metadata generated from them.

## What the report measures

Before opening any capture bytes for classification, the tool calls
the strict `verify_ppu_capture_session.verify()` gate. That rejects
missing/unfinished manifests; missing, altered or truncated PPU/RAM
and optional screenshot files; mismatched frame identifiers or log
prefixes; invalid timestamp ordering and inconsistent event journals.

After verification, the **numerical inventory** reports:

- Which frame labels were saved and how many other frame labels lie
  between successive **selected snapshots** (not a count of missing
  physical frames)
- Whether an independently saved emulator-rendered screen reference
  exists for each verified frame
- Counts of nonzero/unique nametable tile IDs (never the tile IDs
  themselves)
- Changed bytes in each of eight 1 KiB CHR regions, each nametable's
  960 tile cells and 64 attribute bytes, and 32 bytes of palette RAM
- Changed bytes in the RAM queue source $0600–$06FF and changed
  four-byte source slots of RAM page $0700
- Total PPU and RAM byte changes and counts of distinct observed
  CHR/nametable configurations per **raw memory slot**

The tool deliberately does **not** include original graphics bytes,
raw palettes, reconstructed images or original ROM content in its
JSON report.

### What the report does not prove

- **Nametable mirroring:** all four 1 KiB address windows are compared
  as returned by the memory API; mirrored values are not proof of
  four independent nametables
- **MMC3 switching:** a 1 KiB CHR slot may contain several different
  mappings within one displayed frame; end-of-frame snapshots cannot
  establish the entire rendering history
- **Frame and video:** an FCEUX `registerafter` CPU-cycle sample is
  not a verified PPU scanline or physical VBlank boundary
- **Sprites:** RAM $0700 is a possible OAM DMA source, not proof of
  actually displayed sprites or priority
- **Stage identity:** neither verified capture provenance nor the
  report establishes that the sampled scene belongs to Vice:
  Project Doom's first gameplay level
- **Restoration:** original collision/level geometry, camera
  scrolling and new HD art remain unconfirmed/unbuilt

## Tests

Seven additional ROM-free scenarios were added to the existing
`tests/test_ppu_capture_session.py` fixture, exercising the *real*
stage79–87 session validator before analysis: unchanged snapshots;
separate CHR/nametable/attribute/palette/queue/OAM changes;
unchanged-length corruption; unfinished metadata; optional rendered
references; missing CPU-cycle support; and output minimization.
GitHub's Native Core CI runs the regression suite on
`ubuntu-latest`.

The tests use fabricated binary contents. A passing CI is evidence
that the inventory's **software invariants** work, not that real NES
gameplay has been analyzed.

## Practical next step

When an actual **first-level** FCEUX capture has been obtained locally,
inspect which CHR slots and nametable tile/attribute areas vary during
a carefully documented camera movement. Preview only selected frames
using `render_ppu_snapshot.py` and independently corroborate against
emulator-rendered screen references. Do not promote this static
classification to an authentic world map without runtime evidence.
