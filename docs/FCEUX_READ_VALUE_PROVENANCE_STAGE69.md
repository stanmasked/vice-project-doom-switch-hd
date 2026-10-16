# Stage 69 — FCEUX READ callback values are not observed bytes

The documented FCEUX `memory.registerread` callback receives
`(address, size, value)`, **but the third argument is always 0**.
It is a sentinel, not the data read from CPU memory.

Source: https://fceux.com/web/help/LuaFunctionsList.html

## Fixes

- Stage41 pointer RAM reads, stage45 PRG reads, stage49 joint reads and
  stage53 CPU+PRG+MMC3 logs now serialize `READ.value=unknown`.
  MMC3 SELECT/DATA writes retain their actual write bytes.
- All four collectors reject unsupported READ callback signatures, such
  as nonzero or missing sentinels, instead of treating the argument as
  a verified byte. A trapped callback error marks metadata incomplete.
- Stage43, stage44/46, stage50 and stage54 validators reject logs
  claiming actual READ callback bytes; they require explicit
  `read_value_provenance=address_only_fceux_zero_sentinel`.
- Stage55-60 analysis remains address-only, explicitly reporting
  `read_values_proven=false`.
- Stage41 **separately** samples RAM with `memory.readbyte`, but that
  sample is only a callback-time RAM snapshot; it is not proven to be
  the bus value of the triggering instruction.

**Important:** Earlier captures and synthetic fixtures with READ bytes
such as `AB` or `99` must be discarded and recaptured with these
corrected tools. Their apparent data bytes were not evidence. The local
private PRG comparison from stages57-59 is a distinct operation: it
reads a user-supplied raw PRG file, not the READ callback's value.
A byte match from that file still does not prove effective-address or
READ causality.

## Regression checks

The existing ROM-free Lua and Python tests were updated to require
`unknown` for READ and genuine byte values for mapper writes. Negative
tests verify rejection of nonzero READ sentinels and forged READ bytes.
Capture completeness also checks callback-error counts. The stage41
RAM callback regression checks that the separately sampled RAM bytes
remain available even though the triggering READ byte is unknown.

Locally executed: the five synthetic stage53/FCEUX ROM-preflight Lua
scenarios passed using LuaTeX 5.3 with the revised READ semantics. The
other updated Python and Lua fixtures are checked into GitHub but
their successful execution in CI has **not** been demonstrated. GitHub
Actions runner allocation remains externally blocked (historically
`runner_id=0`, zero execution steps). No authentic first-level trace,
game resources, map geometry or Switch binary is claimed.
