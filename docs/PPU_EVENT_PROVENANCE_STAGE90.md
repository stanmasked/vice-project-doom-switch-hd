# Stage 90 — provenance of MMC3 CHR and PPU scroll writes between snapshots

## Scope

Stage89 compares static zero-scroll background reconstructions against
verified FCEUX screen references. A low mismatch fraction alone cannot
establish **when** or **whether** a CPU-visible register value was used
by the actual NES PPU raster.

Stage90 adds a separate numeric audit of **registered CPU callbacks**
between successive *saved-snapshot event checkpoints*:

`tools/audit_ppu_event_provenance.py`

It requires a **fully verified local session** using
`verify_ppu_capture_session.verify()`. The reporter groups exactly
those MMC3/PPU events whose committed record indices fall between
the previous and current snapshot's
`logged_register_writes` value. It does **not** infer writes during
unobserved frames, CPU register values before the capture began, or
the PPU's physical VBlank/scanline position.

## Run locally — keep results out of public GitHub

```bash
python3 tools/audit_ppu_event_provenance.py \
  private/ppu_capture_session.meta.txt \
  --require-cycle \
  --out private/ppu_event_provenance.json
```

`--require-cycle` only rejects an unclocked session. Cycle trace
verification does **not** authenticate PPU timing.

### What is counted

For each committed snapshot interval, counts include:

- MMC3 even/odd register writes, CHR register data writes R0–R5,
  PRG-register data writes, and data writes without a known selector
- CHR inversion transitions with two observed states; before the
  first mode observation the inversion is **unknown**
- PPUCTRL writes and observed changes in its background-pattern bit
- Mirrored PPUSTATUS read markers, PPUADDR writes, PPUSCROLL writes,
  completed pairs, writes before the shared latch was synchronized,
  and first scroll writes interrupted by PPUADDR or PPUSTATUS

PPUSCROLL and PPUADDR share the hardware write toggle. The recorded
PPUSTATUS value is a **zero sentinel** used for read provenance, not
the actual byte returned by the PPU. The first valid latch reset
is not assumed unless a read of $2002 was observed.

The interval is determined by capture **event count**, not a guess at
the time of the PPU's physical frame boundary. The state machine
retains partial latch and CHR-register knowledge across snapshot
windows, with `unknown` remaining unknown until observed.

## Stage89 linkage

`tools/audit_ppu_screen_alignment.py` adds an
`observed_event_window` to both referenced and nonreferenced frames.
It makes CHR and PPUSCROLL event counts available beside static
screen-image comparisons, while continuing to assert
`visible_scroll_or_chr_mapping_proven=false` and
`event_window_to_screen_visibility_proven=false`.

This context is **not** a rendered-raster model, a camera trajectory,
an original level layout or an HD asset. Bank and scroll values are
deliberately excluded from published report fields, as are raw
PPU/RAM bytes and reference image pixels.

## Synthetic tests

- `tests/test_ppu_event_provenance.py` tests the production register
  observation state machine: mirrored MMC3 ports, unknown selector,
  PRG vs CHR writes, CHR inversion, mirrored PPUSTATUS/PPUSCROLL,
  unknown latch, interrupted pairs, PPUCTRL pattern-bit changes,
  and six independently observed CHR registers
- The existing `tests/test_ppu_capture_session.py` also checks the
  **real whole-session integrity gate** before window attribution,
  scroll-pair continuity, stage89 image-context linkage, changed-log
  rejection and unclocked-session handling
- CI uses no original ROM or captured graphics. New assertions test
  software behavior only.

No authentic first-level FCEUX trace or on-hardware Switch run was
obtained during this stage. Do not publish original game captures or
derived graphical evidence from the owner's ROM in this public repo.
