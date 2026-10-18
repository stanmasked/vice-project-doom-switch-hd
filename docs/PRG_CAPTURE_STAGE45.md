# Stage 45 — same-session FCEUX PRG read observation (experimental)

The opt-in `tools/capture_fceux_prg_reads.lua` registers a CPU
$8000–$FFFF read callback and MMC3 $8000/$8001 write callbacks in **one
emulator session**. It writes a bounded `stage45_prg_reads.tsv` in
the private directory, compatible with `tools/audit_prg_read_mapping.py`.
An adjacent metadata file records overflow and completeness.

In FCEUX with an authorized local ROM and an existing private folder:

```lua
VPD_PRG_DIRECTORY = "private/first_level"
VPD_PRG_MAX_EVENTS = 50000
dofile("tools/capture_fceux_prg_reads.lua")
```

Close the Lua script normally to emit metadata. Then run:

```sh
python3 tools/audit_prg_read_mapping.py private/first_level/stage45_prg_reads.tsv --out private/first_level/stage45_bank_audit.json
```

**Evidence restrictions:** the Python stage44 auditor currently validates
TSV events and mapper replay, but **does not parse the stage45 completeness
metadata**. An audit of the TSV alone therefore does not certify complete
capture. Inspect `events_dropped=0` and `complete=yes` separately.
The live FCEUX API read callback signature and full-range hook behavior
must be verified on the actual emulator, rather than inferred from Lua
mocks. No genuine first-level trace was obtained. Neither ROM bytes,
instruction PCs, nor stage geometry are published or established.
