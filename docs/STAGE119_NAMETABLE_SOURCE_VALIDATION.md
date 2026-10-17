# Stage119 — differentiated synthetic nametable source validation

The synthetic Mapper-4 ROM fills nametable space with alternating tile IDs 0 and 1 before enabling rendering. In CHR bank 1, the generated test uses blank even tiles and filled odd tiles; the control uses blank tiles throughout. The two images have byte-identical header and PRG. All ROMs are generated inside private CI directories rather than copied from Vice: Project Doom.

Seven fail-closed Python tests verify the 4096-byte nametable writer, original Stage118 CPU program compatibility, reproducible graphics differences and source-guarded real FCEUX pixel hooks. These are prerequisites, not claims that live coarse-scroll visual differentiation is yet established. Native success must separately corroborate the consumed nametable ID, coarse register, CHR planes and framebuffer in one FCEUX process.

The native PPU patch also saves the actual nametable fetch address in each BGData record immediately after its ID read. At rendering, this per-record address accompanies the tile ID, pattern planes and final XBuf byte. Native and parser reject out-of-range $2000–$2FFF addresses, alternating-parity mismatches, equal source addresses, or absent origin fields. The address evidence is emulator-specific, not hardware-cycle evidence.
