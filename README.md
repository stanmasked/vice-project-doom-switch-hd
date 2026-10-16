# Vice: Project Doom — Native HD Remake Research

**Status:** ROM-free native Switch diagnostic NRO builds successfully. The project is not yet a playable game or HD remake; hardware runtime remains unverified.

This private repository contains an independent C++ research/development toolchain targeting Nintendo Switch Homebrew. No NES emulation engine, original ROM, or game-derived artwork is included.

## Verified milestones

- Original USA ROM analyzed locally: NES 2.0 / mapper 4 (MMC3); PRG 128 KiB; CHR 128 KiB.
- 8,192 2bpp tiles discovered; 7,194 unique tile patterns.
- C++ CHR decoder and atlas exporter pass ROM-free unit tests and the owner's local ROM verification.
- GitHub Actions **Native Core CI** passed: [run #38828092666](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/38828092666).
- GitHub Actions **Nintendo Switch native probe** built and uploaded a ROM-free `.nro`: [run #38828228022](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/38828228022).
- No gameplay restoration, actual HD artwork or Switch hardware test has been confirmed.

## Project folders

| Directory | Purpose |
| --- | --- |
| `native_core/` | C++17 CHR decoder, atlas exporter and unit tests |
| `tools/` | Local-only NES ROM static analysis tools |
| `tests/` | ROM-free Python tests, NRO verifier, private ROM regression check |
| `switch_probe/` | Minimal libnx native Switch executable with no original data |
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
```

## ROM-free Switch diagnostic

With a configured devkitPro devkitA64/libnx toolchain:

```bash
make -C switch_probe
python3 tests/check_nro.py switch_probe/vpd_native_probe.nro
```

You can download the diagnostic NRO under **Artifacts** in the successful [Switch build](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/38828228022). It is not the game.

## Original ROM analysis (locally, never commit generated data)

```bash
python3 tools/inspect_rom.py '/private/path/Vice - Project Doom (USA).nes' --out .
python3 tools/disassemble_fixed_bank.py '/private/path/Vice - Project Doom (USA).nes' --out reports/
mkdir -p switch_viewer/assets
build/native_core/vpd_chr_cli '/private/path/Vice - Project Doom (USA).nes' switch_viewer/assets/
python3 tests/verify_original_rom.py '/private/path/Vice - Project Doom (USA).nes' --cli build/native_core/vpd_chr_cli
```

**Rights and provenance:** Original commercial game binaries, extracted graphics, disassembly and ROM-bearing build artifacts are not published. The project is research tooling; a distributed remake requires appropriate permissions.
