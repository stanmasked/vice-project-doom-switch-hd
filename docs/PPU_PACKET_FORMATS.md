# NMI PPU packet formats — ROM-local static handler decoding

The eight PPU queue command formats are now recoverable from individual
6502 handler code paths. This is **not a runtime trace** or NES emulator.

Each command appears at `$0600,Y`; the byte following the last payload
byte becomes the next command index in RAM `$16`. On command ID 0, the
dispatcher stops. If a command's cost cannot fit in the current NMI
60-unit budget, the dispatcher leaves it queued for the next pass.

| ID | Payload bytes | Static effect |
|---|---:|---|
| 1 | 7 | call bank-dependent routine `$DFC6`, set `$2000`, copy CPU memory bytes to PPU |
| 2 | 0 | upload 16 palette bytes `CPU $0140-$014F` to `PPU $3F00-$3F0F` |
| 3 | 0 | upload 16 palette bytes `CPU $0150-$015F` to `PPU $3F10-$3F1F` |
| 4 | 3 | write one literal byte to chosen PPU address |
| 5 | 12 | two two-byte writes plus one masked PPU update (falls through handler #7) |
| 6 | 7 | same as #1 but with a different scheduling budget |
| 7 | 4 | read/AND/OR/write one PPU byte |
| 8 | 4 | read/AND/OR/write eight PPU addresses, incrementing *low address byte* |

All PPU addresses in the queue are encoded **low byte, high byte**; the
6502 stores the high byte to `$2006` before the low byte.

Handler #1/#6 fields are:
`bank-argument, PPUCTRL, PPU-low, PPU-high, CPU-pointer-low, CPU-pointer-high, count`.
A zero count means **256 bytes**, due to the 6502 `DEX/BNE` loop.
The external bank routine `$DFC6` can change CPU memory mapping, so the
decoder emits a symbolic CPU-to-PPU copy request instead of fabricating
the source bytes from the fixed ROM bank.

Handler #5's last `STA $2007` is followed directly by instruction `INY`
at `$E74D`, the entrypoint for handler #7. It is **not** followed by RTS.
This accounts for the additional four-byte masked update in command #5.

Handlers #7 and #8 depend on buffered PPU reads. Their outputs are kept
symbolic; matching them exactly requires PPU memory/PPUCTRL state captured
during actual execution. Handler #8 increments the low byte of the target
address without carrying into the high byte on overflow.

## Runnable analyzer

~~~sh
python3 tools/decode_ppu_packets.py '/path/to/owned.nes' \
  private/queue_0600.bin \
  --cpu-snapshot private/cpu_64k.bin \
  --out private/ppu_decoded.json
python3 -m unittest discover -s tests -p 'test_decode_ppu_packets.py' -v
~~~

The analyzer checks the original ROM's dispatcher plus **28 handler
instruction anchors** before accepting a queue trace. Its queue input is a
captured 256-byte RAM page, not an image inferred from CHR data. A
64KiB CPU snapshot is optional: without it, palette transfers are
represented by source addresses rather than asserted colors.

**Private data policy:** Captured queue buffers, palette values, RAM
snapshots, original ROM and derived visuals must remain outside GitHub.
Synthetic test fixtures and independently authored analysis code are safe
to share within the project.

## Current gap to the HD remake

This milestone reconstructs how the game updates PPU memory, but **does
not capture the first level's actual palette, nametable, sprite OAM or
active CHR banks**. Next capture the live buffers at title → first-stage
transition and compare successive frames, then render the restored
scene with new independently authored HD art.
