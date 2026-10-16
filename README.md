# Vice: Project Doom — Native HD Remake Research

**Current stage:** research tools and independent native C++ components. This is not a playable port, and no Nintendo Switch hardware build has been verified.

This private repository documents an original, native C++ rebuild targeting Nintendo Switch homebrew. The NES ROM and game-derived graphics are intentionally excluded from source control.

## Repository structure

- `native_core/`: CHR decoder and tests
- `tools/`: ROM analysis scripts, to be run locally with a legally obtained copy
- `switch_viewer/`: experimental native SDL2 research viewer
- `tests/`: ROM-free automated checks
- `docs/`: roadmap and provenance constraints
- `.github/workflows/`: continuous integration

## Local validation

```sh
cmake -S native_core -B build/native_core -DCMAKE_BUILD_TYPE=Release
cmake --build build/native_core --parallel
ctest --test-dir build/native_core --output-on-failure
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Current milestones

1. Reproducible source repository and ROM-free CI
2. Behavioral reference research (MMC3, palettes, maps, actors)
3. Independent deterministic native game simulation
4. New high-resolution artwork and rendering
5. Switch NRO build and hardware testing

**Copyright and provenance:** The original `Vice: Project Doom` ROM, binary assets, derived tile atlas images, and disassembly must stay outside this repository unless suitable distribution rights have been obtained. No copyrighted ROM or game assets are required for CI. See `docs/PROVENANCE.md`.