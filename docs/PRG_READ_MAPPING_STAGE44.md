# Stage 44: PRG read-to-bank audit (preparatory)

`tools/audit_prg_read_mapping.py` audits a *single ordered observation stream*
of MMC3 $8000 SELECT writes, $8001 DATA writes and instrumented CPU-bus
reads in $8000–$FFFF. This is a validator, **not a live read recorder**.

The input is a private TSV with this exact header:

```text
frame seq kind cpu_address value mapped_bank
```

The actual file uses tabs, not spaces. The ordered `kind` values are
`SELECT`, `DATA`, `READ`. Addresses and values are uppercase hex,
bank labels are decimal or `unknown`. Initial MMC3 mode, R6 and R7 are
unknown. The audit replays writes and rejects incorrect labels.

A confirmed physical PRG offset is computed as
`8 KiB * physical_bank + (cpu_address % 8192)`, but is **not** a stage
loader classification. The observed read byte is not independently verified
against any ROM in this tool. No original asset data belongs in Git.

**Do not merge independent stage38 and stage41 logs** into a unified stream:
they are separate sessions without a shared ordering guarantee. A future
FCEUX implementation must capture *reads and mapper writes in one session*,
verify read callback semantics, and bound event volume with dropped-event
metadata before this audit can be used as evidence of real gameplay.

Five synthetic regression tests check unknown initial state, both MMC3
PRG modes, forged mapping, broken ordering, malformed rows, and a read
outside the CPU PRG window. Real first-level observations remain absent.
