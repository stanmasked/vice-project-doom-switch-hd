# Video pipeline: original Vice: Project Doom (NES USA)

## Confirmed ROM-local static evidence

The final PRG bank is mapped at CPU **$E000–$FFFF**. Two short straight-line routines transfer CHR bank identifiers from zero-page RAM through MMC3 bank select ($8000) and bank data ($8001).

| MMC3 CHR register | RAM source | Routine |
| --- | --- | --- |
| R0 | $3D | $E8A3 |
| R1 | $3E | $E8A3 |
| R2 | $3F | $E8B8 |
| R3 | $40 | $E8B8 |
| R4 | $41 | $E8B8 |
| R5 | $42 | $E8B8 |

During boot, the ROM's instructions at $E588–$E590 write **0** to $3D and **2** to $3E. This establishes two **boot-time** values, not the graphics arrangement for any particular stage.

The NMI handler initiates sprite DMA via $4014, invokes a PPU update queue routine ($E5DC), and calls video-mode dispatch ($E7C3). An update queue accesses **RAM $0600,Y**; a command handler writes target PPU addresses to $2006 and data to $2007.

### Correct interpretation of CHR bank registers

MMC3 R0 and R1 select *even-aligned 2KiB pairs*, using their low bit masked off. R2–R5 select four independent 1KiB banks. CHR inversion mode swaps which PPU half (addresses $0000–$0FFF or $1000–$1FFF) receives the two groups. The original cartridge has 128 physical 1KiB CHR banks, and bank selection wraps accordingly.

The analyzer can calculate an **illustrative mapping** from six supplied *observed* register bytes; do not mistake manually supplied examples for actual stage values.

## Reproduce locally

~~~sh
python3 tools/inspect_video_pipeline.py '/private/path/Vice - Project Doom (USA).nes' --out private/video_pipeline.json
python3 tools/inspect_video_pipeline.py '/private/path/Vice - Project Doom (USA).nes' --registers 00,02,04,05,06,07
python3 -m unittest discover -s tests -p 'test_video_pipeline.py' -v
~~~

The analyzer symbolically evaluates only the short register-write routines (no dynamic CPU emulation). The ten verification groups and six synthetic unit tests protect against incorrect assumptions; a modified ROM fails strict validation.

## Remaining research

1. Record live contents of $3D–$42 at game boot, first stage entry, and animation transitions.
2. Observe MMC3 bank selection register $8000 mode bits, accounting for inversion, at frame/scanline boundaries.
3. Recover actual color palettes and nametable/metatile layout, based on the $0600 VRAM command queue.
4. Map those combinations to frames and newly drawn HD equivalents.

**Status:** Neither first-stage geometry, original palettes nor live animation bank sequences have been extracted or validated. No original game art, code dump or ROM content is committed.
