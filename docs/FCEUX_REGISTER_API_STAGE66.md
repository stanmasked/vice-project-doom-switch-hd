# Stage 66 — FCEUX CPU-register API correction

The official FCEUX Lua API exposes CPU registers using
`memory.getregister("a")`, `"x"`, `"y"`, `"s"`, `"p"` (lowercase).
Stage52 and stage53 previously called `emu.getregister`; in FCEUX this
could silently produce only `unknown` register fields.

Corrections:
- Both Lua capture tools now call the documented API and use lowercase names.
- Their metadata includes `register_api=memory.getregister`.
- The stage54 strict validator requires this provenance key, rejecting
  earlier stage53 logs with an unverified getter.
- Stage52 and stage53 callback tests reject the old getter and check
  unknown register handling, mapper updates and event overflow.
- `tests/test_fceux_register_api.lua` checks complete A/X/Y/S/P samples
  for both capture scripts, using only the documented register API.

Local verification used Lua 5.3 through `luatex --luaonly`: the three
synthetic Lua scripts passed. These ROM-free callback mocks are **not
an actual FCEUX runtime compatibility test**; callback timing and
read values still need validation on the actual emulator.

**Previous stage53 captures should be recaptured** before they are used
to derive CPU read candidates. Even valid register samples are not proof
of instruction-to-read causality, first-stage identity, or geometry.
GitHub Actions remains blocked by failures showing no allocated runner
and no executed steps; do not interpret the red checks as confirmed
test failures.
