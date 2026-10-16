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
