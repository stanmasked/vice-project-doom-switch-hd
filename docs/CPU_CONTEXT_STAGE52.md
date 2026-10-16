# Stage 52 — sparse CPU register context (experimental)

`tools/capture_fceux_cpu_context.lua` is a **separate** opt-in FCEUX
register-execution probe for five selected CPU addresses. Its events
contain A/X/Y/S/P when `emu.getregister` is available and returns a valid
byte, otherwise `unknown`. It also records a status showing whether all
five registers were sampled.

Example with a private, existing directory:

```lua
VPD_CPU_CONTEXT_DIRECTORY = "private/first_level"
VPD_CPU_CONTEXT_MAX_EVENTS = 10000
dofile("tools/capture_fceux_cpu_context.lua")
```

Outputs are `stage52_cpu_context.tsv` and its `.meta.txt` partner.
The meta file records overflow and declares that instruction opcodes and
effective addresses are **not recorded**. Captures from this tracer and
stage49 cannot be merged as if they were the same execution session.
CPU register getter availability and callback timing require validation
against the installed FCEUX version.

A ROM-free Lua mock covers available/unavailable registers and overflow;
it is configured in CI but its passing result is not yet confirmed.
No live first-level evidence, map structure or original artwork has
been recovered.
