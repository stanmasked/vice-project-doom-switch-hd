# Stage118 — two live $2005 X/Y pairs and coarse-register provenance

The synthetic pinned-FCEUX experiment now performs two complete horizontal
X + vertical Y register-write pairs during the **same frame** rather than
one write before the frame. The first X sets fine horizontal offset
1, 3, 5 or 7 and coarse horizontal scroll 0. After a CPU DEX/BNE
delay, the second X selects complementary fine 7, 5, 3 or 1 and
coarse horizontal scroll 1 (raw $2005 values 15, 13, 11 or 9).

The private source-guarded native FCEUX PPU hook records both writes
immediately after the upstream assignment to ppur.fh and ppur._ht.
The pixel hook checks 64 positions after each write in its own
visible source scanline and 16 positions in the following line,
including the actual pattern bytes used for background pixels,
bgpx and bgtile. It refuses swapped events, missing writes, wrong
coarse/fine values, inconsistent frame epochs, and forged results.

All four generated mapper-4 ROMs are evaluated in separate native
processes. Each positive record must be accompanied by the existing
stage110 actual final-XBuf same-run witness. Fixed-bank and
observer-disabled ROMs form required negative controls.

**Important distinction:** the second coarse horizontal coordinate
is proven to be written to the internal FCEUX register. The immediate
screen bgtile index is derived from the **fine** offset and raster
position. These observations alone do not prove a visually distinct
nametable/CHR tile caused by the coarse increment. That requires a
follow-on generated nametable-identifying ROM and fetch-to-pixel
provenance. Nothing here proves original Vice: Project Doom raster
behavior, hardware-accurate NES cycles or a completed Switch renderer.
