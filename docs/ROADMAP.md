# Roadmap — native HD remake

## M0: reproducible repository
- [x] C++ 2bpp CHR decoder and CLI.
- [x] Python metadata inspection and conservative fixed-bank disassembler.
- [x] ROM-free unit tests authored for GitHub Actions.
- [x] Private GitHub repository initialized.
- [ ] Verify hosted CI run.

## M1: original behavioral specification
- [ ] Trace MMC3 bank selects at title, stage load and gameplay.
- [ ] Recover PPU palettes, nametables, metatiles and OAM animation frames.
- [ ] Record input/state/timing test cases from legal local copy.
- [ ] Document level and collision formats with confidence levels.

## M2: first native scene
- [ ] Implement fixed-step simulation independent of renderer.
- [ ] Load a reconstructed map as native scene data.
- [ ] Implement player movement, collisions and camera for a representative scene.
- [ ] Add deterministic replay tests.

## M3: first HD scene
- [ ] New hand-authored high resolution textures and character artwork.
- [ ] Native renderer, animation, effects and UI.
- [ ] Compare gameplay timing with original reference captures.

## M4: Nintendo Switch validation
- [ ] Install/test devkitPro/libnx/SDL2 build in clean CI environment.
- [ ] Publish first diagnostic ROM-free .nro artifact.
- [ ] Confirm Switch input/display behavior on hardware.
- [ ] Profile performance in handheld and docked modes.
