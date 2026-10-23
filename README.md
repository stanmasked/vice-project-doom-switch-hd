# Vice: Project Doom — Native HD Remake Research

**Status:** Two ROM-free Nintendo Switch NRO prototypes compile successfully: an ASCII test scene and a **1280x720 native RGBA8888 raster scene** with independently created procedural background and pixel character. The C++ simulation and renderer pass host-side reproducibility tests. Neither NRO is the original game or a playable HD remake; Switch hardware execution remains unverified.

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
| `graphics_core/` | Portable C++ 1280x720 raster renderer, independent synthetic art |
| `switch_graphical/` | Native libnx RGBA8888 framebuffer scene and Switch NRO build |
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

## Stage 22 — ROM-free Nintendo Switch graphical build

The native graphical test scene now compiles on devkitPro/libnx without SDL2
or original NES assets. It draws **1280×720** RGBA8888 pixels using a software
framebuffer and presents our already tested fixed-tick simulation with a
hand-authored procedural skyline, tile platforms, pixel hero, and simple HUD.
This is a diagnostic, not Vice: Project Doom gameplay or actual final HD art.

- Portable host C++ test checks buffer boundaries, golden pixel checksum,
  deterministic scene output, camera motion and invalid input.
- A second host integration test exercises the **actual game_core** simulation,
  including 200 ticks of movement and jump input, then verifies deterministic
  scene changes through the raster renderer.
- The [graphical NRO GitHub Actions run](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/38922369314)
  cross-builds and uploads `vpd-native-raster-scene`, a ROM-free NRO.
- For build and control details, see [switch_graphical/README.md](switch_graphical/README.md).

Actual gameplay physics, original first-stage composition, art restoration,
stable frame pacing, and physical Switch runtime validation remain undone.

## Stage 23 — sprite texture import and animation (ROM-free)

The native Switch diagnostic now consumes a **versioned VPAT v1 RGBA sprite
atlas** with CRC32 checking, alpha blending and frame selection. The
four-frame developer hero asset is independently drawn by
`tools/build_demo_atlas.py` and embedded at build time. For newly authored
HD PNG sprite sheets, `tools/pack_vpat.py` creates a VPAT binary and
C++ resource header, so texture authors do not have to modify renderer code.

- C++ tests reject corrupted headers and checksums, protect framebuffer
  boundaries, and verify idle/run/jump poses actually change the scene.
- Python tests validate PNG alpha, dimensions and frame count.
- The native Switch NRO still has no external asset streaming or RomFS
  hot-reload, and the included art is intentionally provisional.

See [asset pipeline](docs/ASSET_PIPELINE.md) and
[switch_graphical](switch_graphical/README.md). Original NES artwork,
accurate gameplay and on-device performance validation are still outstanding.

## Stage 24 — frame-timed animation controller

Authored sprite animations are now configured through
[assets/demo_animation.json](assets/demo_animation.json), validated by
[tools/build_animation_manifest.py](tools/build_animation_manifest.py)
and compiled into constexpr C++ tables. The renderer accepts an explicit
resolved sprite frame; an independent `AnimationPlayer` handles idle,
run, rise and fall states, clip loops, transition resets and left/right
facing. Horizontal mirroring uses the existing ROM-free VPAT atlas.

The console's **same** simulated movement/gravity and the C++ sprite
renderer are covered by a full deterministic gameplay → animation →
atlas → raster regression. The latest devkitPro build publishes another
native diagnostic NRO. See [animation documentation](docs/ANIMATION_CONTROLLER.md).

The four atlas frames and JSON durations are **author-invented tests**;
original Vice: Project Doom animation timing, final HD character art,
runtime asset streaming and physical-console performance remain open.

## Stage 25 — optional external sprite atlas on SD

An optional author-created 4-frame VPAT resource may now be read from
`sdmc:/switch/vice_project_doom/hero.vpat` at launch and reloaded
in-game with **X**. Pressing **Y** restores the embedded developer
sprite. The on-screen HUD indicates whether external art was accepted
or the last manual reload failed. A bad file does not replace the
last valid resource.

The portable AssetSource loader enforces VPAT v1 length, CRC32,
frame-count compatibility, bounded memory and an atomic replacement
operation. C++ host tests exercise successful loading and failure
rollback, while devkitPro compiles the same code into the Switch NRO.
A separate downloadable blue demo VPAT is a **synthetic test**, not
restored Vice art.

[Installation, controls and safety rules](docs/SD_ASSET_OVERRIDE.md).

This has not been tested on actual Switch hardware, and the game
remains a synthetic scene with placeholder animations and physics.

## Stage 26 — SD animation manifest hot reload

External animation **timing and frame order** are now stored in validated
VANM v1 binary clip data, independent of the VPAT sprite pixels.
The native Switch diagnostic loads `hero.vpat` and optional `hero.vanm`
as one staged resource transaction. If a supplied VANM is corrupt or
incompatible, both current resources remain unchanged. Press **X** to
reload, **Y** to restore embedded art and timing. With no VANM file,
existing stage-25 external VPATs remain compatible using the embedded
four-clip manifest.

The ROM-free [VANM packer](tools/pack_animation_binary.py) accepts the
same authored JSON as the compile-time animation generator. The new
[external animation format documentation](docs/EXTERNAL_ANIMATION.md)
explains clip records, CRC checks, state bounds and SD paths. CI verifies
both the transaction and native NRO cross-build. This is not measured
original-game animation timing and has not been run on physical Switch.

## Stage 27 — animation-to-atlas content binding (VANM v2)

The optional SD-card `hero.vanm` file can now be **VANM v2**, with an
explicit CRC32 of the companion VPAT pixel payload. The runtime validates
both files before switching. It rejects a v2 timeline paired with
*different pixels*, even if the two atlases have identical dimensions
and frame counts. The prior valid atlas and timings remain active on
a mismatch. [Python packing tool](tools/pack_animation_binary.py)
supports the `--atlas` argument to produce a bound VANM v2.

VANM v1 remains readable for older stage-26 SD bundles, but does not
bind to exact pixel content. CRC32 is an accidental-mismatch check,
**not a security signature**. See [VANM v2 documentation](docs/EXTERNAL_ANIMATION.md).

## Stage 28 — independent terrain texture atlas

The native Switch diagnostic now uses a **separate procedural terrain VPAT**
for solid platforms. It is deliberately independent from the hero's
VPAT+VANM resource pair: art changes can be previewed without changing the
collision geometry, hero animation or the code.

An optional independently authored terrain atlas can be installed at
`sdmc:/switch/vice_project_doom/terrain.vpat`. Press **ZL** to reload
it, **ZR** to restore the embedded terrain; **X/Y** still control the hero
bundle. All terrain cells are displayed at 32×32 screen pixels.

Four tile variants and validation/rollback rules are documented in
[TERRAIN_PIPELINE.md](docs/TERRAIN_PIPELINE.md). The original first stage
has **not** been extracted or recreated; no physical Switch runtime
test has been performed.

## Stage 29 — two SD-reloadable parallax background layers

The diagnostic now composes **two independent RGBA background frames**
behind the terrain and sprite. The distant skyline moves with 1/5 camera
offset, the near skyline with 1/2. A transparent sky reveals the prior
gradient, stars and moon. A validated `backdrop.vpat` may override the
compiled-in, original synthetic backgrounds from an SD card, and **L/R**
reload/reset this resource without affecting the hero or ground.

Source: [backdrop generation](tools/build_demo_backdrop.py) and
[BackdropSource](graphics_core/backdrop_source.cpp).
[Format, valid frame sizes, controls and limitations](docs/PARALLAX_BACKGROUNDS.md).
There is still **no verified live NES first-stage capture or physical
Nintendo Switch performance measurement**.

## Stage 30 — independently animated decorative assets

The ROM-free native scene now draws a separate **four-frame alpha VPAT**
for industrial signal lamps and fans, layered both behind the terrain
and in front of the character. Frame choices use deterministic simulation
ticks and positions tied to world coordinates, not physical screen offsets.
Decor art is strictly cosmetic and does not modify hitboxes, map topology,
hero actions or collision simulation.

The independently-authored `decor.vpat` can be replaced at
`sdmc:/switch/vice_project_doom/decor.vpat`. D-pad **Up** reloads the
asset, **Down** returns to the embedded test resource. Other art-control
bindings remain unchanged. File validation and rollback use the same
bounded VPAT loader as earlier stages. Detailed examples are in
[DECOR_EFFECTS.md](docs/DECOR_EFFECTS.md).

A separate synthetic 48×64 editable art sheet and SD-ready VPAT are
available in the conversation. This is **not** recovered NES visual
data; real first-stage scenery and Switch hardware performance are
still outstanding.

## Stage 31 — editable level prop placements

The native Switch diagnostic now loads decoration coordinates, front/rear
layer choice, frame ranges and per-object animation periods from a separate
VLAY v1 scene file. The JSON authoring source and binary packer are in
assets/demo_decor_layout.json and tools/pack_decor_layout.py.

External layouts belong at sdmc:/switch/vice_project_doom/decor_layout.vlay.
Press Minus to reload them or the right-stick button (R3) to restore
built-in placements. Up/Down still change only decorative pixel art.
Invalid layouts do not discard the previously accepted positions.

See docs/LEVEL_PLACEMENTS.md for file structure, schema, examples and
limits. All default object positions and animation periods remain
invented diagnostics, not the actual Vice: Project Doom first stage.

## Stage 32 — measuring the original first stage

The repo now includes a conservative
[PPU capture stitching tool](tools/stitch_stage_captures.py), a
[documented evidence manifest](docs/STAGE_MAP_EVIDENCE.md) and
five invented-data tests. It can merge multiple measured first-stage
8x8 nametable observations into a **private** world-coordinate report,
preserving pixel-memory disagreements rather than inventing a collision
map. The Lua FCEUX acquisition interval and capture limit are now
configurable to obtain overlapping observations.

**Important:** The original NES first stage and its collision geometry
have not yet been extracted; the new tool requires actual FCEUX captures
with independently measured camera/scroll positions. It does not add
proprietary data or claim the native Switch test stage is authentic.

## Stage 33 — static evidence for first-stage scroll research

The [ROM-local audit tool](tools/audit_ppu_scroll_sources.py)
identifies the $E8DE fixed-bank PPU scrolling routine's instruction
sources ($0B, $0D and $0C), verifies ten opcode anchors and runs
six new synthetic tests. The [full findings](docs/SCROLL_SOURCE_AUDIT.md)
separate *register-source evidence* from still-unverified world-camera
behavior. Local ROM-derived reports stay private.

No authentic first-stage geometry has been reconstructed. The Switch
graphical test NRO is unchanged by this research-only milestone.

## Stage 34 — origins of PPU scroll input bytes

A second [original-ROM audit](tools/audit_scroll_writers.py) now
verifies **eight** separate 6502 writer regions in physical PRG
banks 14 and 15, including zero initialization, a packed-byte
decoder and increment/decrement paths for zero-page $0B/$0C/$0D.
Six new invented-ROM tests passed locally. See
[SCROLL_WRITERS.md](docs/SCROLL_WRITERS.md).

Important: $0B/$0C behave as a 16-bit arithmetic pair in several
routines, while $0D has independent update sites. This is not
proof of world camera X/Y or authentic stage geometry. GitHub Actions
has been failing to provision a runner at stage 33–34 commits;
do not mistake those infrastructure failures for passing CI.

## Stage 35 — possible source descriptor pointer

The new [ROM-private pointer audit](tools/audit_indirect_pointer.py)
confirms a bank-12 `$92 → $AA/$AB` table-pointer setup and a bank-14
indirect consumer. The CPU carry behavior is emulated exactly; no
first-stage data table is claimed without dynamic proof.

The [technical findings](docs/INDIRECT_POINTER_TRACE.md) include
six ROM-free locally passing tests, private-only report output and
conditions for correlating real FCEUX execution. GitHub Actions has
been unable to provision its runner; this stage has **not** obtained
a green hosted CI. No Switch NRO changed.

## Stage 36 — the index feeding the candidate stage-data pointer

The [ROM-local index audit](tools/audit_index_92.py) validates six
instruction signatures for RAM `$92`, previously seen forming the
`$AA/$AB` descriptor pointer. A fixed-bank branch cycles 0–21, but
other verified code explicitly loads **147** or sources `$92` through
an indirect read. A 22-state cycle in one code path is **not evidence
of 22 game levels** or the global index domain.

[Full source-level analysis](docs/INDEX_92_AUDIT.md) and seven
fabricated-ROM tests are committed. Live execution, authentic level
format and camera semantics remain unproven. GitHub Actions runner
provisioning is still being checked; hosted CI success is not assumed.

## Stage 37 — conditional state dispatch feeding the RAM $92 index

The [strict index dispatch audit](tools/audit_index_dispatch.py)
confirms **nine** original-ROM 6502 instruction groups and **seven**
static branch/table destinations. RAM $90 value 13 selects table
entry $E4C0, leading to $E4E6; when RAM $91 is nonzero this
branches to $E4F3. That code checks RAM $07 bit 7 first, then
bit 2 before bit 3 to choose among special-state, decrement and
increment paths. Bit 2 wins if both are set.

This is **a verified conditional code path**, not measured execution
during authentic first-stage gameplay. ROM-free regression tests
passed locally; [documentation](docs/INDEX_STATE_DISPATCH.md)
lists every verified destination, mapping caveats and remaining
runtime unknowns. The existing native Switch NRO is unchanged.

## Stage 38 — instrumented FCEUX execution evidence

New [execution logger](tools/capture_fceux_dispatch.lua) records
CPU execution callbacks at confirmed fixed-bank dispatcher code,
candidate bank-switched pointer/decoder addresses, selected RAM
writes and MMC3 $8000/$8001 register history. Unlike static
analysis, it can capture executed PCs in a future actual FCEUX
session, while refusing to guess **initial PRG bank mapping**.

The matching [validator](tools/analyze_dispatch_execution.py)
replays mapper state, rejects false physical bank labels and
incomplete event sequences. Eight invented-event Python tests and
three production-Lua mock configurations pass locally.
See [DISPATCH_EXECUTION_TRACE.md](docs/DISPATCH_EXECUTION_TRACE.md).
**No actual first-stage emulator trace has yet been captured.**
The native Switch NRO is unchanged.


## Private source evidence: Stage 335–336

The current research result confirms the observed RAM-to-PPU scroll-input load/store path using a private original-source FCEUX replay. Only a redacted aggregate is tracked in Git; the original ROM/FM2, raw traces, instruction sites, source hashes, and byte values remain in private storage.

- [Stage 335–336 findings and limits](docs/DRIVING_PRIVATE_STAGE335_RAM0D_PPU_SCROLL_INPUT.md)
- [Redacted public aggregate](docs/stage335_public_aggregate.json)
- [Aggregate safety/consistency audit](tools/audit_public_stage335_aggregate.py)

The audit is deliberately aggregate-only and fails if raw source identifiers or unproven camera/road semantics are published.
