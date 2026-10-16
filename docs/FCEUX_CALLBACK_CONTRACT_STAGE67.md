# Stage 67 — validate the real FCEUX Lua callback contract

FCEUX's current Lua function reference documents memory read/write callbacks
as `(address, size, value)` with byte writes having `size == 1`:
https://fceux.com/web/help/LuaFunctionsList.html

Older FCEUX documentation describes a two-argument callback without a
value:
https://documentation.help/FCEUX/%7BD3F1816D-0770-4257-98D2-A21456B07D28%7D.htm

The stage53 trace **requires the third byte argument** for memory READ and
MMC3 register writes. It must not interpret missing bytes as a trustworthy
observation. This stage adds strict callback checking in
`tools/capture_fceux_joint_cpu_context.lua`:

- READ and mapper writes require valid CPU addresses, `size == 1` and an
  integer value between 0 and 255. MMC3 SELECT/DATA must occur at precisely
  $8000/$8001 respectively.
- Sparse EXEC callbacks must report the expected CPU PC and `size == 1`.
  They do not use the callback's value to infer opcodes.
- Any callback mismatch increments `callback_errors` and raises an
  explicit exception. If FCEUX invokes the registered exit callback, its
  metadata records `complete=no`. If the exception prevents metadata
  creation, the validator rejects the missing metadata.
- New metadata includes `callback_contract=address_size_value_v1` and
  `callback_errors=0` for valid captures. The stage54 validator rejects
  older stage53 logs without those keys, or with nonzero errors.

In particular, the older stage53 captures are no longer suitable for
instruction-to-read candidate comparisons: recapture in a **single**
original-game session after verifying the FCEUX version's API.
`tests/test_fceux_callback_contract.lua` tests five malformed callback
shapes alongside valid later events. Existing tests for stages52/53 and
the register API have also been updated.

## Verification and limitations

Four synthetic Lua tests ran locally with `luatex --luaonly` using Lua
5.3 and passed. GitHub CI may remain blocked before runner allocation; do
not conflate that with a demonstrated test failure. No live FCEUX session,
actual original ROM, video or first-level map has been validated.
Documentation and mocks establish expected API behavior, **not proof** of
correct data access semantics, instruction identity or level geometry.
