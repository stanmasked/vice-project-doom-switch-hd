# Stage 68 — fail-closed FCEUX ROM preflight

Before stage53 opens its private trace file, it calls
`tools/fceux_rom_preflight.lua` to inspect only the 16-byte iNES header
of the ROM **currently loaded in FCEUX**.

For the documented USA *Vice: Project Doom* board (NES-TLROM/MMC3), the
accepted profile is:
- iNES format (NES 2.0 is intentionally not supported by this check);
- mapper 4 (MMC3);
- 128 KiB PRG ROM (8 x 16 KiB iNES PRG units);
- 128 KiB CHR ROM (16 x 8 KiB iNES CHR units).

Board profile evidence:
https://nescartdb.com/profile/view/195/vice-project-doom
and https://nesdir.github.io/753768A6_USA.html.
The iNES header structure is documented at
https://www.nesdev.org/wiki/INES.

This is a **compatibility check**, not an independently authenticated
game or regional-revision identification. Another ROM may share this
header. To additionally prevent accidental image switching, set an
expected full-ROM MD5 obtained independently from your private file.
The local expected digest is never embedded in a generated trace or
committed to Git. This does **not** compare against the stage59 raw-PRG
SHA-256: whole-file ROM MD5 and headerless PRG SHA-256 are different.

## Running stage53 in FCEUX

1. Load your **own existing** USA NES ROM in a compatible FCEUX build.
2. Create a private output directory *outside tracked source files*.
3. In the FCEUX Lua console, run from the project root:

```lua
VPD_STAGE53_DIRECTORY = "private/first_level"
VPD_STAGE53_MAX_EVENTS = 20000
-- Optional: pin to an independently recorded digest of the loaded FULL NES file:
-- VPD_STAGE53_EXPECTED_ROM_MD5 = "32_hex_digits_from_private_ROM"
dofile("tools/capture_fceux_joint_cpu_context.lua")
```

If mapper, header, PRG/CHR size or the optional MD5 disagrees,
the script raises an error **before** opening the TSV. The header
reader requires `rom.readbyteunsigned` or `rom.readbyte`;
MD5 checking also requires `rom.gethash("md5")`.

Successful captures add `rom_header_profile=ines_mapper4_prg128k_chr128k`
and `rom_md5_pin=matched` or `not_supplied` to stage53 metadata.
The stage54 validator rejects older traces without compatible profile
metadata, but cannot independently attest that metadata has not been
fabricated. An unpinned capture remains unverified as to game identity.

## Testing and evidence limits

```sh
luatex --luaonly tests/test_fceux_rom_preflight.lua
luatex --luaonly tests/test_fceux_capture_preflight.lua
luatex --luaonly tests/test_fceux_joint_cpu_context.lua
luatex --luaonly tests/test_fceux_register_api.lua
luatex --luaonly tests/test_fceux_callback_contract.lua
```

All five synthetic Lua scenarios passed locally. They exercise
rejected image profiles, optional digest mismatches, early no-TSV
failure, successful metadata, register sampling and invalid callbacks.
They do not execute the real game or verify FCEUX runtime semantics.
GitHub Actions still needs an allocated runner before it can verify
the same tests in CI.

No original game resources, capture files or privately supplied
digests are included in this branch. Live first-level trace, opcode
causality, geometry and Nintendo Switch builds remain outstanding.
