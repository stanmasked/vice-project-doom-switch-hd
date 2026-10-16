# Vice: Project Doom — Native HD Remake Research

**Status:** A ROM-free deterministic side-scrolling test scene compiles into a native Nintendo Switch NRO and passes C++ replay tests. This is not original Vice: Project Doom gameplay, not an HD remake yet, and is not tested on Switch hardware.

This private repository contains an independent C++ research/development toolchain targeting Nintendo Switch Homebrew. No NES emulation engine, original ROM, or game-derived artwork is included.

## Verified milestones

- Original USA ROM analyzed locally: NES 2.0 / mapper 4 (MMC3); PRG 128 KiB; CHR 128 KiB.
- 8,192 2bpp tiles discovered; 7,194 unique tile patterns.
- C++ CHR decoder and atlas exporter pass ROM-free unit tests and the owner's local ROM verification.
- GitHub Actions **Native Core CI** passed: [run #38828092666](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/38828092666).
- GitHub Actions **Nintendo Switch native probe** built and uploaded a ROM-free `.nro`: [run #38828228022](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/38828228022).
- Original ROM-free C++ physics/collision/camera scaffolding passes Debug/Release CI: [run #38829149333](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/38829149333).
- Native interactive ASCII-scene NRO built and uploaded: [run #38829200654](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/38829200654).
- Original gameplay restoration, HD artwork and Switch hardware validation remain outstanding.

## Project folders

| Directory | Purpose |
| --- | --- |
| `native_core/` | C++17 CHR decoder, atlas exporter and unit tests |
| `tools/` | NES ROM analysis plus local FCEUX PPU/OAM capture, background/sprite preview |
| `tests/` | ROM-free Python/Lua/C++ tests, NRO verifier and private ROM regression check |
| `game_core/` | Native deterministic game-scene scaffold with placeholder physics and map |
| `switch_probe/` | Native libnx ASCII test scene with D-pad/A/B gamepad input |
| `switch_viewer/` | Experimental SDL2 CHR page viewer (requires private generated pages) |
| `docs/` | Development roadmap and provenance/copyright guidelines |
| `.github/workflows/` | Host-side CI and native Switch probe build |

## Host-side builds and tests

```bash
cmake -S native_core -B build/native_core -DCMAKE_BUILD_TYPE=Release
cmake --build build/native_core --parallel
ctest --test-dir build/native_core --output-on-failure
python3 -m pip install 'Pillow>=10,<13'
python3 -m unittest discover -s tests -p 'test_*.py' -v
cmake -S game_core -B build/game_core -DCMAKE_BUILD_TYPE=Release
cmake --build build/game_core --parallel
ctest --test-dir build/game_core --output-on-failure
```

## ROM-free Switch diagnostic

With a configured devkitPro devkitA64/libnx toolchain:

```bash
make -C switch_probe
python3 tests/check_nro.py switch_probe/vpd_native_probe.nro
```

You can download the ROM-free native test-scene NRO under **Artifacts** in [Switch Actions #38829200654](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/38829200654). It shows an ASCII scene, not the original game. See [native simulation notes](docs/NATIVE_SIMULATION.md).

## Original ROM analysis (locally, never commit generated data)

```bash
python3 tools/inspect_rom.py '/private/path/Vice - Project Doom (USA).nes' --out .
python3 tools/disassemble_fixed_bank.py '/private/path/Vice - Project Doom (USA).nes' --out reports/
mkdir -p switch_viewer/assets
build/native_core/vpd_chr_cli '/private/path/Vice - Project Doom (USA).nes' switch_viewer/assets/
python3 tests/verify_original_rom.py '/private/path/Vice - Project Doom (USA).nes' --cli build/native_core/vpd_chr_cli
```

**Rights and provenance:** Original commercial game binaries, extracted graphics, disassembly and ROM-bearing build artifacts are not published. The project is research tooling; a distributed remake requires appropriate permissions.

## Local FCEUX snapshot and static OAM sprite reconstruction

The NES background and sprite snapshot tools are **analysis aids**, not a
full emulator or accurate live rendered stage. See
[REFERENCE_CAPTURE.md](docs/REFERENCE_CAPTURE.md) for the complete workflow.

- `tools/capture_fceux_ppu.lua` records 16KiB PPU, 2KiB CPU work RAM
  and a bounded register log (with an explicit overflow warning).
- `tools/render_ppu_snapshot.py` reconstructs the unscrolled background.
- `tools/render_oam_sprites.py` adds a static OAM sprite overlay, including
  8x8/8x16 patterns, flip, palette selection and basic priority.
- `tools/compare_ppu_captures.py` summarizes changes between saved frames.
- GitHub CI runs the actual Lua capture script against a synthetic FCEUX API,
  plus Python unit tests, without including the game's original assets.

Authentic first-stage captures and on-hardware Switch testing are **not done**.


## Stage 19: rendered-screen reference and MMC3 frame log

The FCEUX Lua capture can now save the *emulator's rendered screen*, not just
the end-of-frame PPU address space. The ROM-free comparison tool
[compare_rendered_frame.py](tools/compare_rendered_frame.py) compares captured
NES palette indices with our static reconstruction, producing mismatch
heatmaps and a per-scanline summary. The RGB image is preserved independently
for reference.

[analyze_mmc3_frame_log.py](tools/analyze_mmc3_frame_log.py) reconstructs
ordered MMC3 CHR R0-R5 writes and available 1KiB bank maps across logged
frames. It **cannot** recover scanline/cycle positions from a frame-number
TSV, nor fill in missing initial register values.

Local synthetic tests, FCEUX API mocks, and GitHub CI pass; **the original
first level has not been captured in FCEUX**. All real-game images, memory
dumps, and logs remain local and private. See [capture documentation](docs/REFERENCE_CAPTURE.md).
