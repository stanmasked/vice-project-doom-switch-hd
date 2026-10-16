# Stage 38 — FCEUX execution-gated index-dispatch trace

**Status: tooling and synthetic tests only. No genuine first-stage FCEUX
execution has been captured or proven; the original level and world camera
remain unreconstructed.** This document does not distribute any game ROM.

## Capture actual CPU execution privately

Create a writable Git-ignored folder, open your legally held NES image
in desktop FCEUX, and run the following in its Lua script window:

```lua
VPD_TRACE_DIRECTORY = "private/first_level"
VPD_TRACE_MAX_EVENTS = 20000
VPD_TRACE_SESSION_LABEL = "manual_first_stage_attempt"
dofile("tools/capture_fceux_dispatch.lua")
```

The label is user-supplied and is **not validated by FCEUX**. Run the
focused execution logger separately from the older video-capture script
until interaction between their hooks has been verified. Stop the Lua
script normally so the exit callback writes final metadata.

Two private files are produced:

- stage38_dispatch_exec.tsv: timestamped (if available) ordered CPU
  execution callbacks, tracked RAM writes, $8000/$8001 mapper writes,
  and sampled RAM $07/$90/$91/$92/$AA/$AB/$A8/$A9.
- stage38_dispatch_exec.meta.txt: ROM MD5, manually supplied session
  label, counts, dropped event flag and initial-state limitations.

The event count is bounded (default 20,000; permitted 1..500,000).
If events are lost, the session is marked incomplete, not silently
accepted. The callback's cycle counter can be unavailable or reset.

## Which addresses are instrumented

Eleven known CPU addresses in the fixed last PRG bank 15:
$E418, $E479, $E4E6, $E4F3, $E500, $E50F, $E519, $E522,
$E8DE, $E8EA and $E8EF.

Four CPU addresses have a **conditional physical bank identity**:

| CPU address | Candidate physical bank |
|---|---:|
| $835B | 12 (pointer setup) |
| $C906 | 14 (packed-byte consumer) |
| $C138, $C1C8 | 14 (alternate index writers) |

The hooks are real FCEUX `memory.registerexec` hooks. The documented
API only identifies a CPU address, not a physical ROM bank:
https://fceux.com/web/help/LuaFunctionsList.html

## Correct MMC3 PRG mapping

The script begins with **unknown** mapper state, R6 and R7. A
$8000 write supplies the PRG-mode bit 6 and register selection;
an $8001 write supplies R6/R7 only after matching selection.

- Mode 0: CPU $8000=R6, $A000=R7, $C000=bank 14, $E000=bank 15.
- Mode 1: CPU $8000=bank 14, $A000=R7, $C000=R6, $E000=bank 15.

In mode 1, a callback at CPU $835B is **not** evidence of bank-12
pointer setup. Until the mapper's relevant writes are observed,
its physical bank is unknown rather than guessed.

## Validate and summarize private logs

```sh
python3 tools/analyze_dispatch_execution.py \
  private/first_level/stage38_dispatch_exec.tsv \
  --meta private/first_level/stage38_dispatch_exec.meta.txt \
  --out private/first_level/stage38_execution_audit.json
```

The standalone Python validator replays the observed MMC3 register
history. Wrong bank labels, missing/reordered event sequences, malformed
rows, invalid ROM-hash format or incomplete records are rejected.
The optional --allow-incomplete switch keeps an explicit false
completeness flag for diagnostics; it does not certify a trace.

The summary distinguishes execution at a given CPU PC from execution
at a PC **while the correct physical bank was observed mapped**.
An observed bank-12 setup preceding a bank-14 decoder is only a
candidate ordered pair; it does not prove the pointer was preserved
or identify the data as a first-stage map.

RAM bytes read from a write callback may be the **pre-write** state,
depending on emulator callback semantics. Follow-up validation requires
CPU-cycle register observations and scene-confirmed video references.

## Tests and next steps

Eight invented-event Python tests check bank replay, missing events,
incomplete traces, corrupted mapper labels, ROM identity, timestamp
contracts, and unexpected PCs. Three synthetic Lua tests run the
production logger with/without cycles and on deliberate overflow.
Separately, the nine fixed-bank opcode anchors and seven branch edges
of stage 37 were reverified against the owner's original ROM.

**A real first-stage capture has not been performed.** Native Nintendo
Switch graphics and collision code are unchanged by this milestone.
