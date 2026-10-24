# Stage356 — authenticated original early-scene uniformity and PPU mask diagnostic

**Provenance: exploratory reanalysis of previously exposed Stage355 frames 380–404. This is NOT a freshly preregistered/held-out result.** Stage355's locked RGB motion gate remains FAILED/INCONCLUSIVE, with 24/24 preregistered texture pairs ambiguous and eight frames missing a required first vertical $2005 register-write anchor. Neither source masks nor results were retroactively changed.

## Original evidence independently reauthenticated

The owner-private Stage355 original 25 native 256×240 XBuf RGB images and source CPU/native PPU traces were obtained from the permanent private archive, not recomputed or synthesized. The independent original 32-source-file SHA-256 manifest seal and individually sealed Stage335/341 full 261-frame CPU/native-PPU traces were verified again; the read-only original FM2 completion marker and classic PPU NewPPU=0 provenance were retained.

The **25 entire source RGB frames are byte-identical** (one unique whole image, 24/24 identical adjacent raster pairs). Furthermore every one of the 25 original images contains **one and the same RGB color across all 61,440 pixels**; three separately captured full indexed palette planes are also identical. Therefore no image-only estimator can establish a unique vertical displacement from any chosen ROI in these source frames. The prior Stage355 24/24 *inconclusive* image-motion labels are the correctly cautious outcome.

## New Stage356 native PPU mask and CPU event diagnostics

Original CPU event evidence and *native classic PPU line-zero* mask witnesses, each authenticated by the prior full trace seals:

| Independently checked event category | Original 380–404 frames |
| --- | ---: |
| Native line-zero event anchor present | 25 |
| No first/second-phase $2005-related CPU bus write in source trace | **8** |
| At least one qualifying second-phase CPU write | **17** |
| Native line-zero PPU mask equals zero | **9** |
| Zero mask *and* absent second-phase CPU write | **8** |
| Zero mask with a second-phase write still present | **1** |
| Missing second-phase write with line-zero mask nonzero | **0** |

For the eight source frames with no qualifying CPU write, the native zero rendering mask provides an independently observed contextual distinction: the emulator records a PPU output-disabled line-zero state in the same original frames. The additional ninth source frame shows zero mask **while a qualifying CPU write is still present**, so mask state and CPU write presence must not be conflated.

This is documented event **co-occurrence**, not direct proof that the mask produced the entire 25-frame uniform RGB span, that zero mask automatically means no camera motion, or that a missing CPU write implies the previous Y byte was preserved unchanged. The entire RGB span also includes 16+ frames with nonzero native mask; all are single-color in the captured XBuf. We cannot infer any vehicle/road physics from this material.

## Repository output and privacy boundary

- `tools/audit_private_stage356_early_ppu_mask.py` — owner-local authenticated original source reader; independent prior-hash checks; verifies 32 manifest source members, 261-frame CPU/native PPU anchors and every native 256×240 GD original image; emits **only bounded numeric aggregate and explicit unsupported conclusions**.
- `tests/test_stage356_early_ppu_mask.py` — **16 fabricated-only unit tests** for identical/flat images, blank texture as non-motion, missing CPU writes, separate ninth zero mask, conflicting mask/write evidence and explicit non-claims.
- `docs/stage356_public_diagnostic.json` — public counts only, no original game data, full PPU trace rows, source registers, ROM/FM2 bytes, pixels, capture Lua or owner-private file digests.

All original raster/CPU/PPU data stay in the owner-only [Stage355 original evidence ZIP](https://drive.google.com/file/d/1aIb6glmFOjgaq5mCADHkVSeLqSHo5Dn4/view). Stage356 numerical audit script, private runtime log, source manifest reference, checksum receipt and handoff are independently archived in owner-only Google Drive Project Evidence Archive (no duplication of copyrighted original ROM or FM2).

## Next work

Stage357 should establish a **new, independently predeclared state-transition diagnostic** for a fresh, unsampled interval, or trace exact classic PPU register retention through consecutive source events using a separate, clearly labeled exploratory analysis. A PPU line-zero mask readout is not a hardware cycle/dot measurement. Prespecify expected negative controls and never reinterpret Stage355's originally failed 4-mask motion gate as a pass. Keep Draft PR #99; main remains unchanged.
