# Stage 49 — joint CPU PC, PRG read and MMC3 observations

The optional `tools/capture_fceux_joint_exec_reads.lua` emits one
same-session ordered TSV with `EXEC`, `READ`, `SELECT` and `DATA`
callbacks. It hooks five *candidate* execution PCs and the cartridge
CPU-window reads, and replays mapper bank-state without inventing the
initial values. An overflow marks the session incomplete.

Run in a local FCEUX Lua session with an existing private folder:

```lua
VPD_JOINT_DIRECTORY = "private/first_level"
VPD_JOINT_MAX_EVENTS = 20000
dofile("tools/capture_fceux_joint_exec_reads.lua")
```

Output: `stage49_joint.tsv` and `stage49_joint.meta.txt`.
The older stage44 auditor **cannot** parse this new schema; a dedicated
strict validator is still needed before using it as evidence. The callback
order is merely an observation: the preceding instrumented PC need not
be the instruction responsible for the next read. Execution hooks are
sparse, CPU registers and instruction lengths are not captured, and
read callbacks may include instruction fetches. CPU effective address
and opcode/data distinction are not established.

A synthetic Lua test verifies ordering, unknown-to-mapped MMC3
transitions and overflow; the test does not establish real FCEUX
callback semantics. Original first-level footage, complete live
traces and stage geometry remain unavailable. Do not commit the ROM,
derived assets, or local trace data.
