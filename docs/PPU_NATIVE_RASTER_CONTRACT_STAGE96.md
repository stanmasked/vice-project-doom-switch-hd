# Stage96 — candidate native PPU raster trace contract

This stage defines a **ROM-free contract and validation tool** for a future
native FCEUX PPU instrumentation hook. No real FCEUX PPU hooks were installed,
and no original game raster samples were recorded.

## Contract

The synthetic generator writes two private files:
- `ppu_raster_manifest.json`: pinned 40-hex candidate build revision,
  before/after tick hook phase, source class, NTSC timing model, event/frame
  counts, SHA-256 checksum, zero dropped events and zero counter discontinuities
- `ppu_raster_events.tsv`: four TSV columns
  `frame<TAB>scanline<TAB>dot<TAB>kind`, with no register values or pixels

Allowed event kinds: frame_anchor, pixel_fetch_sample, chr_context,
scroll_context, ppu_write, vblank_enter, vblank_exit. NTSC coordinates are
scanlines 0–261 and dots 0–340. Each complete frame begins with an anchor
at (0,0), has a VBlank start at (241,1) and a VBlank end at (261,1).
These positions reflect the documented **NES NTSC model**. They are NOT
independent FCEUX measurements. All frames must be consecutive; events
must be ordered and complete.

The validator recomputes SHA-256 from the original bytes and independently
rejects malformed-but-rehashed TSV streams. An intact SHA-256 file alone
does not authenticate an emulator, ROM, or source build. Even
source_class=candidate_native_unverified produces **untrusted** evidence.
Independent build/hook review and golden-trace testing are mandatory.

## Run a synthetic smoke test (no ROM)

```bash
python3 tools/make_synthetic_ppu_raster_trace.py private/stage96_synthetic --frames 2
python3 tools/verify_native_ppu_raster_contract.py \
  private/stage96_synthetic/ppu_raster_manifest.json \
  --out private/stage96_synthetic/audit.json
python3 -m unittest discover -s tests -p 'test_native_ppu_raster_contract.py' -v
```

The emitted aggregate JSON reports only event counts and explicit unknowns.
It NEVER claims actual VBlank observation, correct PPU hook timing,
CPU/CHR/scroll-to-pixel causality, original game geometry, or HD readiness.
Real captures, raster event logs and derived game-specific reports stay
private and out of GitHub.

## Next engineering gate

Implement a native exporter pinned to an exact FCEUX source revision,
document before/after PPU tick semantics, frame/odd-dot skipping, VBlank
state, MMC3 bank effects and clock discontinuities; independently compare
its **synthetic** trace to expected NTSC PPU behavior. Only then consider
private original-first-level captures and verified background/world mapping.

Reference: https://www.nesdev.org/wiki/PPU_rendering and
https://www.nesdev.org/wiki/PPU_registers
