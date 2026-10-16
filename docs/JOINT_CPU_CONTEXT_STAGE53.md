# Stage 53 — one-session CPU context + PRG/MMC3 observations

The opt-in `tools/capture_fceux_joint_cpu_context.lua` combines five
candidate execution hooks, CPU $8000-$FFFF read callbacks and MMC3
register writes in one ordered private TSV. Optional A/X/Y/S/P register
samples are collected via `memory.getregister` with lowercase register
names at callback time; unsupported registers are
`unknown`, never imputed.

Use an existing private output folder in a local FCEUX session:

```lua
VPD_STAGE53_DIRECTORY = "private/first_level"
VPD_STAGE53_MAX_EVENTS = 20000
dofile("tools/capture_fceux_joint_cpu_context.lua")
```

Outputs: `stage53_joint_context.tsv` and
`stage53_joint_context.meta.txt`. Metadata marks overflow as incomplete.
The stage54 validator `tools/validate_joint_cpu_context.py` validates the
stage53 schema and capture metadata; live authenticity is still unverified.
Sampling register values does not prove an instruction generated a READ;
callback ordering, opcode, and effective addresses remain unverified.

The Lua mock test is ROM-free; live FCEUX API behavior and original
first-stage runtime evidence remain outstanding. Do not commit ROMs,
memory dumps, captured footage or game-derived resources.
