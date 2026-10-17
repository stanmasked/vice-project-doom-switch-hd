# Stage 77 — PPU video tracer: full mirrored MMC3 coverage

## Why the change matters

The original `tools/capture_fceux_ppu.lua` hooked only specific CPU
addresses `$8000/$8001/$A000/$C000/$C001/$E000/$E001`. The MMC3
decodes **four pairs across the entire $8000–$FFFF range**, with
different even/odd registers in each 8 KiB window. In particular:

- `$8000–$9FFF` even: bank select + PRG/CHR mode; odd: bank data.
- `$A000–$BFFF` even/odd: mirroring and PRG RAM protect.
- `$C000–$DFFF` even/odd: IRQ latch and reload.
- `$E000–$FFFF` even/odd: IRQ disable and enable.

Hardware specification: https://www.nesdev.org/wiki/MMC3#Registers
FCEUX size-range callback documentation:
https://fceux.com/web/help/LuaFunctionsList.html

The previous hooks could miss CHR bank changes made through
`$8002/$8003`, resulting in a misleading `chr_r0–chr_r5`
snapshot even though the original CPU address was recorded correctly
elsewhere in the project.

## Changes

- The PPU collector now installs one
  `memory.registerwrite(0x8000,0x8000,on_write)` callback covering
  **every** MMC3 register mirror. It preserves actual CPU addresses
  in both frame and CPU-cycle TSV files.
- Only even/odd writes within `$8000–$9FFF` change inferred CHR bank
  selection/data. Other MMC3 registers are logged but cannot
  accidentally change CHR state.
- Unexpected write or PPUSTATUS-read callback shapes increment
  `callback_errors` before raising. A per-frame metadata report
  declares `register_log_complete=yes` only when no drops and no
  callback errors were observed.
- New fields `mmc3_write_coverage=full_8000_ffff_even_odd` and
  `callback_errors=N` are written to completed private frame metadata.
- The frame and CPU-cycle Python analyzers replay mirrored bank
  select/data writes by range and parity, not only canonical
  `$8000/$8001`. The cycle analysis metadata gate rejects old
  incomplete-coverage captures or captures with callback errors.
  The scroll analysis CLI likewise rejects such metadata when
  `--metadata` is provided.

The PPU port hooks remain separately limited to canonical
`$2000/$2001/$2005/$2006/$2007`. Their CPU-address mirrors are
**not** covered in this stage. The generated per-frame metadata is
a callback-time snapshot, not proof of exact rendered scanline state
or the identity of the first level.

## Synthetic tests

- `tests/test_fceux_ppu_mmc3_mirrors.lua`: executes the actual Lua
  capture script against mocked FCEUX. Exercises bank selection and
  CHR writes through `$8002/$8003` and `$9FFE/$9FFF`, and other
  mirrored pairs through `$A002/$BFFF/$C006/$DFFF/$E00E/$FFFF`.
  Checks recorded address values, CHR registers and metadata, then
  injects malformed write and PPUSTATUS read callbacks in the next
  frame and expects `register_log_complete=no`.
- `tests/test_mmc3_frame_log.py`: verifies mirrored CHR writes,
  preserving unrelated MMC3 register events.
- `tests/test_ppu_cycle_trace.py`: checks mirrored CPU-cycle events,
  missing metadata coverage and nonzero callback errors.
- `tests/test_fceux_ppu_session_invalidation.lua`: mock updated for
  the documented three-argument range-hook registration.

The Lua test is added to the existing GitHub Actions native job. These
new tests have **not** been fully executed on an up-to-date local
checkout here, and they are not proof of correct live FCEUX operation.
GitHub Actions may still fail without an allocated runner. No original
ROM, captured video, PPU graphics or Switch binary is included.
