# Stage 74 — MMC3 mirrored bank-register writes

## Hardware finding

On MMC3, bank-select and bank-data registers are mirrored across
**CPU $8000-$9FFF**. An even CPU address ($8000, $8002, ... $9FFE)
selects the internal target register and PRG/CHR mode; an odd CPU
address ($8001, $8003, ... $9FFF) writes its value.

Source: https://www.nesdev.org/wiki/MMC3#Registers

Previous FCEUX collectors watched only `$8000` and `$8001`. A game
using, for example, `STA $8002` then `STA $8003` could silently
change mapper state without the event appearing in our log. Subsequent
CPU addresses might then be attributed to the **wrong physical PRG
bank** even though the trace claimed complete event coverage.

## Production corrections

The collectors for stages **38, 45, 49 and 53** now install one
`memory.registerwrite(0x8000, 0x2000, callback)` hook. They classify
each write as SELECT (even) or DATA (odd) according to its **actual**
address, and retain the original CPU write address in the TSV. The
existing MMC3 R6/R7/mode replay is unchanged.

The respective Python validators — `analyze_dispatch_execution.py`,
`audit_prg_read_mapping.py`, `validate_joint_trace.py`, and
`validate_joint_cpu_context.py` — now accept bank writes anywhere
in that address range only with the correct SELECT/DATA parity.
Writes outside the window or with the wrong parity remain invalid.

A new metadata declaration is mandatory:

```text
mmc3_write_coverage=full_8000_9fff_even_odd
```

The validators reject earlier captures lacking that declaration.
This is necessary because a legacy log cannot establish that all
mapper bank changes were observed. This declaration describes the
installed hooks; it is not independent proof of real FCEUX execution,
ROM authenticity or first-stage data identity.

## Regression coverage

Updated synthetic Lua mocks for stages 38, 45, 49 and 53 exercise
mirrored writes, including `$8002/$8003` and `$9FFE/$9FFF`.
Updated Python tests check valid replay, invalid parity and
rejection of legacy incomplete-coverage metadata.

Five stage53/preflight synthetic Lua scenarios were run locally
against the updated callback behavior using `luatex --luaonly`;
all five passed. The complete original source tree and full Python
regression suite were **not** locally executed. The recent GitHub CI
failure remained pre-runner (zero test steps), and therefore is not
evidence of passing or failing unit tests.

No ROM bytes, game level assets or screenshots were added. Future
authentic captures need to be generated again using the updated
hooks; no proof of level geometry or Nintendo Switch gameplay is
claimed.
