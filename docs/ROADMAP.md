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
- [ ] **Run** FCEUX capture during title and first-stage transitions; no verified live captures yet.
- [ ] Capture actual queued packets, palette RAM and PPU state during **runtime**.
- [ ] Recover real PPU palettes, nametables, metatiles and OAM frames.
- [ ] Produce timed local reference traces for movement/collisions/AI.
- [ ] Recover level formats, collision metadata and state transitions.
- [ ] Record confidence levels and local-ROM reproducibility.

The original fixed bank's documented control flow is in [VIDEO_PIPELINE.md](VIDEO_PIPELINE.md) and [PPU_QUEUE.md](PPU_QUEUE.md), and [PPU_PACKET_FORMATS.md](PPU_PACKET_FORMATS.md). See [REFERENCE_CAPTURE.md](REFERENCE_CAPTURE.md) for the new local capture workflow. First-stage palettes, actual runtime sprite mapping, and complete geometry are **not yet restored**.

## M2: first independent native scene — scaffold verified
- [x] Model fixed-step deterministic simulation without an NES interpreter.
- [x] Create an independently authored 64x15 collision test scene (not original stage data).
- [x] Add deterministic replay/behavioral tests in Debug + Release (Actions #38829149333).
- [x] Build independent controllable ASCII scene into native Switch NRO (Actions #38829200654).
- [ ] Recover authentic scene geometry and player motion from ROM-local reference traces.
- [ ] Match character motion/collisions/animation to measured original behavior.
- [ ] Replace the ASCII console output with an actual HD renderer.

## M3: first genuinely HD scene
- [ ] Create new hand-authored characters, backgrounds and effects.
- [ ] Add HD renderer, animation, camera and interface.
- [ ] Evaluate quality against reference scene and original timing.

## M4: Switch platform validation
- [x] Compile a ROM-free libnx diagnostic .nro in devkitPro CI (#38828228022).
- [x] Validate NRO magic/size and upload artifact to GitHub Actions.
- [x] Build native ROM-free ASCII scene diagnostic NRO (Actions #38829200654).
- [ ] Test this ROM-free probe on physical Switch hardware.
- [ ] Integrate the actual native scene, controller, renderer and audio.
- [ ] Profile hardware performance in handheld and docked mode.

**Caution:** The new .nro is an independent ASCII test-scene prototype, not the original game, not an HD remake, and not hardware-validated. The SDL2 CHR viewer build remains unverified. See docs/NATIVE_SIMULATION.md.
