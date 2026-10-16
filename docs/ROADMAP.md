# Roadmap — Vice: Project Doom native HD remake

## M0: reproducible repository — completed
- [x] C++17 2bpp CHR decoder and command-line exporter.
- [x] Python ROM metadata and conservative static 6502 disassembler.
- [x] Synthetic ROM regression and compiled C++ tests.
- [x] Private GitHub repository with provenance exclusions.
- [x] Hosted GitHub Actions native core CI successful (#38828092666).

## M1: restore documented original behavior — next
- [ ] Capture MMC3 PRG/CHR bank changes across title/stage/gameplay.
- [ ] Recover real PPU palettes, nametables, metatiles and OAM frames.
- [ ] Produce timed local reference traces for movement/collisions/AI.
- [ ] Recover level formats, collision metadata and state transitions.
- [ ] Record confidence levels and local-ROM reproducibility.

## M2: first independent native scene
- [ ] Model fixed-step deterministic simulation without an NES interpreter.
- [ ] Convert one validated scene into original game-independent scene data.
- [ ] Match character motion/collisions/animation to recorded reference behavior.
- [ ] Add deterministic replay/behavioral tests.

## M3: first genuinely HD scene
- [ ] Create new hand-authored characters, backgrounds and effects.
- [ ] Add HD renderer, animation, camera and interface.
- [ ] Evaluate quality against reference scene and original timing.

## M4: Switch platform validation
- [x] Compile a ROM-free libnx diagnostic .nro in devkitPro CI (#38828228022).
- [x] Validate NRO magic/size and upload artifact to GitHub Actions.
- [ ] Test this ROM-free probe on physical Switch hardware.
- [ ] Integrate the actual native scene, controller, renderer and audio.
- [ ] Profile hardware performance in handheld and docked mode.

**Caution:** The working diagnostic .nro is a console probe, not a port/remake. The experimental SDL2 CHR viewer build has not yet been verified.
