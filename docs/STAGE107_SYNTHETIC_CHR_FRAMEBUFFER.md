# Stage107: synthetic CHR bank-to-framebuffer proof

Stage106 observed native MMC3 CHR writes, not pixel changes. Stage107
compares two private, independently generated, original mapper-4 ROMs.
All ROM bytes are identical except the bank-select byte in four copies
of the 6502 program. CHR bank 0 is empty; CHR bank 1 is FF-filled.
The ROM initializes contrasting BG palette colors and selects background
pattern table $1000, which MMC3 command 2 maps.

A guarded, opt-in newppu hook after the final XBuf framebuffer assignment
aggregates 32768 visible, background-only pixels. Two native runs must
prove opposite background pattern occupancy and differing hashes of
actual final framebuffer bytes. A third run checks that opt-out emits
no positive marker. PPU source code is patched only in CI's private
pinned FCEUX build; no ROM, source frame, pixel position, or screenshot
is checked into the repository.

Native CI success would prove bank-to-pixel causality for the synthetic
test ROM only. It would NOT prove original-game CHR effects, camera
behavior, first-stage map geometry, or original-screen restoration.
Unit mocks alone are not a substitute for the native FCEUX CI run.
