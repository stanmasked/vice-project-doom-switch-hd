# Stage119 — distinctive nametable IDs, real CHR bytes and XBuf pixels

Stage118 proved two $2005 X writes during one pinned FCEUX synthetic
frame and verified that coarse-horizontal `_ht` changed 0→1, but
it did not prove that a different tile was actually rendered.

Stage119 generates a separate mapper-4 ROM which, while rendering is
disabled, writes alternating tile IDs 0,1 across $2000–$23FF with
PPU $2006/$2007. Its CHR bank1 includes two contrasting 8×8
patterns: tile0 has low/high bitplanes 0x00; tile1 has both planes
0xFF. CHR bank0 remains blank. Four ROMs apply the stage118
fine/coarse scroll pairs 1→15, 3→13, 5→11 and 7→9.

The private hook observes the real upstream PPU buffered name-table
byte `bgdata.main[bgtile].nt`, both pattern-plane bytes, fine-X
pixel position, the actual background pattern and final `XBuf`
pixel byte. It compares the first 16 pixels of the row after the
first write with 16 pixels of the row after the second write;
the coarse increment must change the nametable identity at x=0
from 0 to 1 and pattern 0 to 3, with distinct real XBuf colors.

An undifferentiated-CHR ROM and a probe-disabled ROM are independent
negative controls. The normal uniform-CHR stage110 positive proof
is intentionally **not** used for this distinct-tile experiment;
its register-write/scanline observer supplies timing provenance
without importing an all-FF framebuffer conclusion.

All assets are synthetic and generated only inside private CI
temporary directories. This does not establish original Vice:
Project Doom scroll behavior, genuine NES PPU cycle accuracy,
real game art, or an implemented Nintendo Switch HD renderer.
