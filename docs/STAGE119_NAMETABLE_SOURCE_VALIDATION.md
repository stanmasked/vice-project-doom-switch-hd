# Stage119 — differentiated synthetic nametable source validation

The synthetic Mapper-4 ROM fills nametable space with alternating tile IDs 0 and 1 before enabling rendering. In CHR bank 1, the generated test uses blank even tiles and filled odd tiles; the control uses blank tiles throughout. The two images have byte-identical header and PRG. All ROMs are generated inside private CI directories rather than copied from Vice: Project Doom.

Seven fail-closed Python tests verify the 4096-byte nametable writer, original Stage118 CPU program compatibility, reproducible graphics differences and source-guarded real FCEUX pixel hooks. These are prerequisites, not claims that live coarse-scroll visual differentiation is yet established. Native success must separately corroborate the consumed nametable ID, coarse register, CHR planes and framebuffer in one FCEUX process.
