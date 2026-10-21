# Stage 33 — verified PPU scroll-source instructions in the original NES ROM

## Status and provenance

This is **static reverse engineering of the user's locally held Vice:
Project Doom (USA) NES ROM**, not an emulator runtime measurement and not
a completed first-stage map. No original ROM, nametable contents, game
art, opcode dumps or derived visual assets are committed to GitHub.

A new ROM-local script
[`audit_ppu_scroll_sources.py`](../tools/audit_ppu_scroll_sources.py)
validates ten instruction anchors in the MMC3 fixed 8KiB PRG bank.
It refuses unknown/revised instruction bytes by default. The exact
per-ROM report belongs under ignored `private/`.

## Verified static instruction chain

In the original fixed bank normally mapped to CPU **$E000–$FFFF**, one
PPU scroll writer begins at **$E8DE**:

| CPU location | Verified instruction | What can be concluded |
|---|---|---|
| $E8DE | `LDA $0C` | Reads candidate PPUCTRL nametable bit from zero-page $0C |
| $E8E0 | `AND #$01` | Keeps the lowest bit |
| $E8E2 | `ORA $00` | Combines it with the existing value at $00 |
| $E8E4 | `STA $2000` | Writes PPUCTRL |
| $E8E7 | `LDA $2002` | Reads PPUSTATUS, resetting the shared $2005/$2006 write toggle |
| $E8EA | `LDA $0B` | Loads the first scroll value |
| $E8EC | `STA $2005` | Writes the first PPUSCROLL value |
| $E8EF | `LDA $0D` | Loads the second scroll value |
| $E8F1 | `STA $2005` | Writes the second PPUSCROLL value |
| $E8F4 | `RTS` | Returns |

A fixed-bank direct-call signature at **$E89D** is
`JSR $E8DE`. This verifies an apparent call site, but not its frequency
or the effective values during first-stage gameplay.

In this routine **$0B supplies the first $2005 write; $0D supplies
the second; $0C contributes one bit to $2000**. These are *video register
sources*. There is not yet evidence that they equal the world camera X/Y,
collision coordinates or the exact effective scroll at visible scanlines.

The conservative PRG scan found **16 literal potential $2005 store
instructions in the fixed bank**. It is not a control-flow proof for
every candidate. Additional PRG-bank byte matches can reside in
switchable code or data and receive **no invented fixed CPU addresses**.

## Reproduce with your local ROM

```sh
python3 tools/audit_ppu_scroll_sources.py "private/Vice - Project Doom (USA).nes" \
  --out private/stage33_scroll_audit.json
python3 -m unittest discover -s tests -p 'test_audit_ppu_scroll_sources.py' -v
```

All public tests use invented 6502 fragments and synthetic 128KiB PRG
buffers, including rejection of corrupted opcode anchors and refusal
to assign fixed CPU addresses to a switchable bank. The production
script was run separately against the original owner-provided ROM.

## FCEUX reference capture improvement

The Lua script now records three additional metadata fields at the
moment a snapshot is taken:

- `scroll_emitter_ram_0b`
- `scroll_emitter_ram_0c`
- `scroll_emitter_ram_0d`

It also records
`scroll_emitter_provenance=static_emitter_e8de_not_confirmed_runtime`.

These values are **postframe RAM samples**, not proof that the $E8DE
routine ran or that the bytes represent the on-screen scroll at
capture time. A running FCEUX session must still verify instruction
execution, CPU-cycle history, register state and HUD/IRQ scroll splits.
The actual FCEUX Lua script is regression-tested against a synthetic
API in CI, **not a live recording of the game**.

## Next verification steps

1. Record real first-stage FCEUX snapshots and timestamped $2005,
   $2000, $2002 and MMC3 register events.
2. Verify execution of $E8DE and match the two actual emitted values
   to the captured $0B/$0D RAM values at the same CPU-cycle moment.
3. Trace the writes **into** $0B/$0C/$0D in the appropriate code banks;
   establish which (if any) encode the world camera.
4. Obtain independently measured world-coordinate origin and a stable
   active scanline range for the [stage tile stitcher](STAGE_MAP_EVIDENCE.md).
5. Recover actual collision metatiles, stage entities and events by
   separate analysis; PPU graphics alone do not establish them.

**Neither original first-stage geometry nor an authentic Switch remake
is established by this milestone.** No new NRO is required to test
this research-only code.


## Stage 153 — real emitter execution validation

On 21 October 2026, actual local FCEUX 2.6.5 playback of the user's matching
USA ROM+FM2 confirmed this previously static instruction chain at runtime.
Independent execution callbacks observed PC addresses $E8DE, $E8E4, $E8E7,
$E8EC, $E8F1 **321 times each** over original frames 600–920. Each of those
321 ordered groups had CPU-cycle offsets **0, 9, 13, 20, 27** from $E8DE.

A separate real-FCEUX CPU-write log confirmed the $2000 write at +9 cycles
and both $2005 writes at +20/+27 cycles. All 321 first/second scroll writes
matched RAM $0B/$0D read at the emitter's execution callback. Zero source
ROM/graphics bytes were copied to GitHub. See
[ORIGINAL_STAGE_TRANSITION_CONTRACT.md](ORIGINAL_STAGE_TRANSITION_CONTRACT.md).

This **supersedes the older "static but not executed" status above only for
this specific instruction path and this original movie interval**. The Lua
API has no direct memory.registerread callback in the current FCEUX package;
instead we observed execution of the separately source-verified
LDA $2002 instruction at $E8E7 (+13 cycles). This provides CPU instruction
execution evidence for the status read, but not a measured PPU scroll latch
trace at every pixel or scanline. Effective displayed scroll and camera
motion remain unverified, as do other possible writers and raster splits.

Reproducible source-only private tools:
- tools/capture_private_e8de_instructions.lua
- tools/audit_private_e8de_exec.py
- tests/test_audit_private_e8de_exec.py
- tests/test_private_e8de_instruction_callbacks.lua

Only invented-data tests are suitable for public CI. Keep all genuine
CPU-event and instruction traces, the ROM, the FM2 and screenshots private.


The two late $2005 instructions were also identified at runtime:

- Fixed-bank $E369 executes the **third** $2005 write, value 00.
- Fixed-bank $E36C executes the **fourth** $2005 write, value 00.
- Both are observed once per frame in all 321 checked Stage 1-1 frames.
- Across all 1,284 writes, original CPU write-event cycles exactly equal the
  executing writer-PC callback cycles (zero mismatches).

The first and second writes remain $E8EC and $E8F1, with $0B/$0D matching
CPU register values at the earlier $E8DE callback. The later writer addresses
identify **which instruction executed**, not which visible scanline or pixel
received the PPU scroll state. Private trace sources are local only.
