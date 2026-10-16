# Roadmap — Vice: Project Doom native HD remake

## M0: reproducible repository — completed
- [x] C++17 2bpp CHR decoder and command-line exporter.
- [x] Python ROM metadata and conservative static 6502 disassembler.
- [x] Synthetic ROM regression and compiled C++ tests.
- [x] Private GitHub repository with provenance exclusions.
- [x] Hosted GitHub Actions native core CI successful (#38828092666).

## M1: restore documented original behavior — underway
- [x] Identify all six fixed-bank MMC3 CHR register sources (RAM $3D-$42).
- [x] Verify boot-time R0/R1 values and NMI PPU queue / sprite DMA instruction anchors.
- [x] Add ROM-free static video pipeline tests and 1KiB CHR inversion/even-alignment mapper.
- [x] Confirm GitHub CI on video pipeline research (Actions #38862362193).
- [x] Identify 8 NMI PPU command IDs and 7 distinct handlers (Actions #38862831232).
- [x] Confirm $0600 queue and 60-unit per-pass budget, without treating it as clock cycles.
- [ ] Capture **live** MMC3 CHR register values and bank mode at title/stage/gameplay.
- [x] Decode all 8 PPU command payload formats as **symbolic effects**, including palette halves, CPU copy and masked writes.
- [x] Validate 28 handler instruction anchors and test the queue parser with ROM-free inputs (Actions #38863927572).
- [x] Implement FCEUX Lua snapshot capture and PPU background renderer (Actions #38865231340).
- [x] Validate background tile/attribute/palette decoding against ROM-free synthetic samples.
- [x] Validate the real Lua capture script against a synthetic FCEUX API (GitHub CI #38866707731).
- [x] Fix silent register log truncation; capture metadata now reports write losses.
- [x] Add static OAM sprite preview with 8x8/8x16, flips, palette, transparency and priority (CI #38866828175).
- [x] Reference rendered-screen capture contract (RGB and NES palette indices), synthetic Lua mock CI #38914936801.
- [x] Palette-index screen-vs-PPU comparison and 6 invented-data tests, CI #38915109352.
- [x] Frame-level MMC3 R0-R5 register-log reconstruction and 4 synthetic tests, CI #38915678628.
- [x] Implement normal 2x2 NES nametable scroll and scrolled OAM-vs-background priority (Actions #38917772203).
- [x] Add PPUSTATUS-read ($2002) event marker, paired $2005/$2006 write-toggle analyzer and Lua mock (Actions #38918480183).
- [x] Document limitations, especially Y=240..255, raster splits and unknown initial PPU latch in [PPU_SCROLL.md](PPU_SCROLL.md).
- [x] Add separate CPU-cycle-timestamped MMC3/PPU log using documented FCEUX debugger counter.
- [x] Parse CPU-cycle timelines with reset epochs, unknown initial CHR state and strict capture-completeness metadata.
- [x] Six synthetic Python regression cases and FCEUX Lua mock test; see [CPU_CYCLE_CAPTURE.md](CPU_CYCLE_CAPTURE.md).
- [ ] Validate camera/scroll and actual CPU-cycle timestamp fidelity against real FCEUX title/first-stage recordings.
- [ ] **Run** FCEUX capture during title and first-stage transitions; no verified live captures yet.
- [ ] Capture actual queued packets, palette RAM and PPU state during **runtime**.
- [ ] Recover real PPU palettes, nametables, metatiles and OAM frames.
- [ ] Produce timed local reference traces for movement/collisions/AI.
- [ ] Recover level formats, collision metadata and state transitions.
- [x] Stage 32: create strict FCEUX nametable-tile mosaic reconstruction with per-frame camera/scroll provenance, overlap counts and explicit conflicts ([STAGE_MAP_EVIDENCE.md](STAGE_MAP_EVIDENCE.md)).
- [x] Reject missing ROM identity, incomplete capture log, misaligned tile phase and invalid PPU frames; five invented-snapshot tests.
- [x] Enable opt-in dense first-stage FCEUX capture (e.g. 8 frames / 96 samples), synthetic Lua mock in CI.
- [ ] Record **real** first-stage PPU frames with verified camera/scroll, and populate the evidence-gated tile mosaic.
- [x] Stage 33: verify fixed-bank $E8DE PPU scroll procedure; $0B and $0D feed the two $2005 writes, $0C contributes one PPUCTRL bit ([SCROLL_SOURCE_AUDIT.md](SCROLL_SOURCE_AUDIT.md)).
- [x] Audit literal PPU port writer candidates without treating all byte matches as executable; six ROM-free negative/positive tests.
- [x] Capture $0B/$0C/$0D zero-page values in FCEUX metadata with explicit postframe/static-source caveat, synthetic Lua mock.
- [x] Stage 34: verify eight exact ROM writer signatures for $0B/$0C/$0D across physical PRG banks 14 and 15 ([SCROLL_WRITERS.md](SCROLL_WRITERS.md)).
- [x] Trace the packed-byte transformation from ($AA),Y and distinguish two-byte increment/decrement operations on $0B/$0C from separate $0D updates.
- [x] Add six ROM-free synthetic regression cases, mutation rejection and MMC3 bank-mode caveats.
- [x] Stage 35: verify a bank-12 RAM $92 → $AA/$AB pointer setup, a bank-14 indirect decoder and local JSR anchor ([INDIRECT_POINTER_TRACE.md](INDIRECT_POINTER_TRACE.md)).
- [x] Emulate 6502 pointer-address ADC carry exactly, including incorrect naive base+3×index extrapolation at index 86; six ROM-free tests passed locally.
- [x] Record candidate $92, $AA/$AB, $A8/$A9 postframe RAM samples in FCEUX metadata, never claiming observed execution.
- [x] Stage 36: verify six original-ROM instruction anchors establishing a $92 seed=21, conditional wrap 0..21, alternate seed=147 and indirect writer ([INDEX_92_AUDIT.md](INDEX_92_AUDIT.md)).
- [x] Prove wrap only for one code path, preserving the stage-35 carry caveat and unknown global index domain.
- [x] Add seven ROM-free synthetic audit tests, including mutated anchors and out-of-domain transitions.
- [x] Sample RAM $90/$91/$93 beside $92 in FCEUX postframe metadata with explicit static-only provenance.
- [x] Stage 37: anchor the fixed-bank state dispatcher $E479, table entry $E4C0 -> $E4E6, gate $E4E8 -> $E4F3 and RAM $07 bit-7/2/3 branch priorities ([INDEX_STATE_DISPATCH.md](INDEX_STATE_DISPATCH.md)).
- [x] Verify nine original 6502 instruction signatures, seven relative/table destinations and seven synthetic host tests, including conflicting RAM $07 bits.
- [x] Stage 38: add focused FCEUX CPU execution-hook trace for $E479/$E4E6/$E4F3 and banked $835B/$C906, recording RAM writes and MMC3 $8000/$8001 history ([DISPATCH_EXECUTION_TRACE.md](DISPATCH_EXECUTION_TRACE.md)).
- [x] Reconstruct physical PRG mapping strictly from observed MMC3 register writes, leaving initial mode and R6/R7 unknown; reject inconsistent, truncated or incomplete traces.
- [x] Add eight ROM-free Python validation tests and three synthetic FCEUX Lua mock configurations; host-tested with Lua 5.4 and Python.
- [ ] Identify runtime states selected through RAM $90/$91 and verify the physical meaning of RAM $07 bits in live FCEUX.
- [ ] Dynamically trace the pointer ($AA),Y, bank switching and writer execution in the actual first level.
- [ ] Independently identify actual collision metatiles and event/entity positions; observed PPU tile IDs alone are not collisions.
- [ ] Record confidence levels and local-ROM reproducibility.

The original fixed bank's documented control flow is in [VIDEO_PIPELINE.md](VIDEO_PIPELINE.md) and [PPU_QUEUE.md](PPU_QUEUE.md), and [PPU_PACKET_FORMATS.md](PPU_PACKET_FORMATS.md). See [REFERENCE_CAPTURE.md](REFERENCE_CAPTURE.md) for the new local capture workflow. First-stage palettes, actual runtime sprite mapping, and complete geometry are **not yet restored**.

## M2: first independent native scene — scaffold verified
- [x] Model fixed-step deterministic simulation without an NES interpreter.
- [x] Create an independently authored 64x15 collision test scene (not original stage data).
- [x] Add deterministic replay/behavioral tests in Debug + Release (Actions #38829149333).
- [x] Build independent controllable ASCII scene into native Switch NRO (Actions #38829200654).
- [ ] Recover authentic scene geometry and player motion from ROM-local reference traces.
- [ ] Match character motion/collisions/animation to measured original behavior.
- [x] Add ROM-free native software raster renderer at 1280x720 (independent art).
- [x] Cross-build graphical libnx NRO and upload artifact (Actions #38921850038).
- [x] Guard 1280x720 renderer against stride overflow, incorrect dimensions and regressions via golden screenshot hash.
- [x] Host integration test proves the real fixed-step game simulation drives the renderer and camera (Actions #38922369314).
- [x] Implement validated sprite atlas decoding, alpha compositing, clipping and four-frame animation on native raster NRO (Actions #38924413702).
- [x] Build synthetic 96x32 RGBA atlas at compile-time and import newly authored PNG sprite sheets with VPAT PNG converter.
- [x] Verify malformed sprite data and pose changes with C++ tests; PNG importer has 5 ROM-free tests.
- [x] Separate animation clips and state transitions from the raster scene (see [ANIMATION_CONTROLLER.md](ANIMATION_CONTROLLER.md)).
- [x] Add transactional external VPAT loading from SDMC with embedded fallback (Stage 25).
- [x] Test corruption/oversized/wrong-frame rejection, atomic rollback and NRO cross-build.
- [x] Render invented collision platforms using a separately authored four-tile terrain VPAT atlas (stage 28).
- [x] Support independent ZL/ZR SD reload/fallback for terrain alongside existing X/Y character bundle controls.
- [x] Verify geometry validation, corrupted resource rejection and rollback in host tests, native NRO cross-build (#38932788496).
- [x] Implement two separate VPAT alpha skyline layers, parallax speeds 1/5 and 1/2 camera movement, and tile-safe horizontal repeats (Stage 29).
- [x] Support independent SD background replacement at `backdrop.vpat`, L reload / R reset, and preserve working art on invalid reload.
- [x] Test transparent sky, rendered pixel changes, negative scroll, CRC/geometry rejection and NRO build (Actions #38934661070).
- [x] Add independent 4-frame RGBA decorative object atlas with animations, world scroll and back/front layer ordering (Stage 30).
- [x] Allow independent Up/Down SD reload/fallback for decor.vpat with malformed-resource rollback and automated regression.
- [x] Validate decor effects in native libnx NRO and C++ render tests (Actions #38936912738).
- [x] Move synthetic decoration positions, layers, frame assignments and animation periods to authored VLAY layout data (Stage 31).
- [x] Support an optional SD VLAY layout with Minus reload and R3 reset; validate CRC, bounds and last-good rollback.
- [x] Verify native Switch NRO and twelve host C++ graphics regressions (Actions #38938449747).
- [ ] Replace procedural test scene with original behavior and newly authored HD artwork.

## M3: first genuinely HD scene
- [ ] Create new hand-authored characters, backgrounds and effects.
- [x] Validate native RGBA8888 framebuffer drawing, synthetic background, collision geometry and camera.
- [x] Build an independently authored sprite atlas import/render infrastructure (see [ASSET_PIPELINE.md](ASSET_PIPELINE.md)).
- [x] Implement a data-driven, validated author-authored animation timing manifest; compiled C++ controller, four states and horizontal mirroring.
- [x] Verify deterministic full-stack simulation → animation → sprite atlas → raster output in CI (Actions #38926608121).
- [x] Add independently authored VANM v1 external animation clips and editable durations (stage 26).
- [x] Verify paired SD atlas + timing update is transactional, retains legacy atlas-only fallback and rejects bad data.
- [x] Host test and native cross-build of bundle loader; see [EXTERNAL_ANIMATION.md](EXTERNAL_ANIMATION.md).
- [x] Add VANM v2 optional pixel-content CRC binding, same-count wrong-atlas rejection and legacy v1 compatibility (stage 27).
- [x] C++/Python regression: cross-file checksum and rollback when unrelated art uses the same frame layout.
- [x] Add editable independently authored terrain textures and safe hot reload; see [TERRAIN_PIPELINE.md](TERRAIN_PIPELINE.md).
- [x] Independently reload two background layers without changing collision map or hero/terrain; see [PARALLAX_BACKGROUNDS.md](PARALLAX_BACKGROUNDS.md).
- [x] Add reproducible synthetic industrial lamps and fans, alpha effects and deterministic frame durations; see [DECOR_EFFECTS.md](DECOR_EFFECTS.md).
- [x] Add editable ROM-free placement manifest and VLAY binary packer for decoration authoring.
- [ ] Add detailed original HD character art and measure authentic animation timings.
- [x] Allow opt-in author-created external 4-frame VPAT pixel replacement via SD, X reload and Y fallback.
- [ ] Optimize HD rendering and validate speed on Switch hardware.
- [ ] Evaluate quality against reference scene and original timing.

## M4: Switch platform validation
- [x] Compile a ROM-free libnx diagnostic .nro in devkitPro CI (#38828228022).
- [x] Validate NRO magic/size and upload artifact to GitHub Actions.
- [x] Build native ROM-free ASCII scene diagnostic NRO (Actions #38829200654).
- [x] Build ROM-free native 1280x720 graphical NRO (Actions #38921850038).
- [x] Build the diagnostic NRO with optional runtime SD atlas loading (Stage 25).
- [ ] Test the graphical NRO and actual SD asset replacement on physical Switch hardware.
- [ ] Integrate the actual native scene, controller, renderer and audio.
- [ ] Profile hardware performance in handheld and docked mode.

**Caution:** Both the original ASCII NRO and new graphical NRO are independently authored test scenes, not the original game or a completed HD remake. Neither has been validated on real Switch hardware. See [NATIVE_SIMULATION.md](NATIVE_SIMULATION.md) and [switch_graphical README](../switch_graphical/README.md).
