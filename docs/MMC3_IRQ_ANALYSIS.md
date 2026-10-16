# MMC3 IRQ scheduler — static evidence and limitations

The locally provided USA ROM has a five-byte record table from CPU **$E10D**
through **$E1D9**, immediately before the IRQ interrupt entrypoint at **$E1DA**.
This is **41 rows / 205 bytes**, with **16 distinct handler entry addresses**.
The data was analyzed locally and the original records are **not in Git**.

## How the rows were identified

The ROM-local 6502 code at $E0B0 reads RAM $36 and tests its least significant
bit. For an odd value, the code at $E0B8–$E0C0 computes a five-byte row offset:
`5 * ($36 >> 1)` (8-bit X, so hardware wraparound applies). Then it reads:
- `LDA $E10D,X` → RAM `$34` (low byte of a handler pointer)
- `LDA $E10E,X` → RAM `$35` (high byte)
- `LDA $E10F,X` → MMC3 `$C000` (IRQ latch), followed by `$C001` reload
  and `$E001` enable.
- `LDA $E110,X` → RAM `$33`
- `LDA $E111,X` → RAM `$38`

The IRQ path contains `JMP ($0034)` at $E1F3. All 41 handler pointers fall
inside the CPU $E000–$FFFF fixed ROM bank and begin with a decodable official
6502 instruction.

## What this does *not* prove

- That all 41 rows execute in normal play, or what game states use each row.
- The full semantic meaning of fields stored into RAM $33 and $38.
- Exact video scanline timing, screen split positions, sprite layouts, or colors.
- That these offsets hold for other regional revisions or patched ROMs.

## Reproduce with your local ROM

```sh
python3 tools/inspect_irq_schedule.py '/path/to/owned.nes' \
  --strict --summary-only --out private/irq_schedule.json
python3 -m unittest discover -s tests -p 'test_irq_schedule.py' -v
```

The tool validates 11 fixed-bank instruction anchors before describing the
rows, and the unit tests use fabricated ROM data. The JSON output contains
game-derived row values and therefore belongs only in an ignored private
directory, never in the repository or CI artifacts.

## Follow-up

Instrument RAM $36 and IRQ execution in a locally configured emulator to
identify actual row reachability, handler sequencing, and PPU register effects.
This can inform the **native HD renderer** without embedding the original ROM
or porting an NES emulator into the Switch executable.
