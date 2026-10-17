# Stage103 — CPU $2002 read-to-clear VBlank status in pinned FCEUX

Stage102 observed three source-level PPU_status |= 0x80 and PPU_status = 0
assignments in FCEUX FCEUX_PPU_Loop, with intervals in cumulative
internal emulator tick units. These are not measured NES hardware events.

Stage103 distinguishes CPU reads of PPUSTATUS at $2002. In pinned FCEUX
static DECLFR(A2002), the emulator constructs a returned byte from
PPU_status before its independent PPU_status &= 0x7F read-clear operation.
The debugger guard can suppress clearing: the new hook is inside the
actual clearing branch, and only enabled with newppu selected.

## Verifiable integration

tools/inject_fceux_ppustatus_read_probe.py requires original upstream
source with Git blob ce84a9df2c12b737fb13316737add1e9963a3ff7,
and exact byte-for-byte Stage98+Stage102 patched content. It fails
closed if the native A2002 handler or unique read-clear site has moved,
if hooks already exist, or if source endings are mixed.

The hook requires VPD_NATIVE_RAW_PPU_PROBE and
VPD_NATIVE_SYNTHETIC_PPUSTATUS_READ compile flags, plus
VPD_STAGE103_PPUSTATUS_READ_PROBE=1 at runtime. No callback is installed
in a normal default build.

## Independent synthetic CPU program

tools/make_stage103_ppustatus_poll_rom.py constructs an original NROM
with blank CHR, and a minimal CPU loop:

    C000: LDA $2002
    C003: JMP $C000

This code runs under actual FCEUX with newppu on Xvfb/X11. It is
generated locally in private runner temp; no commercial ROM is used.

At exactly 16384 PPUSTATUS read callbacks, only aggregated counts
are printed: reads where the CPU returned high VBlank bit, reads
where the bit was high before the clear, reads that cleared a high bit,
reads that incorrectly remained high and any disagreement.

A valid report must have returned_high = before_high = cleared_high > 0,
after_high = 0 and invalid = 0. A second real-FCEUX run explicitly
disables the observer, must stay alive for the observation interval,
and must not emit a positive marker.

## Trust and privacy limits

A CPU $2002 read can clear the bit before any frame-loop assignment
does so. Stage102 source assignment intervals therefore are not a
complete VBlank-flag history. Both stages observe FCEUX source-level
behavior in software, not physical NES VBlank pins or rendered pixels.

No ROM data, returned register byte, raw scanline positions, screenshots,
CHR data, or game maps are exported. Original level geometry, mapper
visual causality and HD background substitution remain unverified.
HD replacement stays disabled.

To run independent synthetic regression tests:

    python -m unittest discover -s tests -p 'test_fceux_stage103_ppustatus_reads.py' -v

Original FCEUX source:
https://github.com/TASEmulators/fceux/blob/8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8/src/ppu.cpp
