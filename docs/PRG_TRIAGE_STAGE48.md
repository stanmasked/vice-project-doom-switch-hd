# Stage 48 — PRG reads: code or data remains unverified

The stage45 callback stream includes CPU reads from PRG-ROM space but does not
record executing instruction PCs, effective addresses or instruction operands.
Therefore address continuity alone cannot distinguish instruction fetches
from data reads.

`tools/triage_prg_reads.py` runs the strict stage46 metadata audit and
stage47 run grouping, then records each candidate as
`indeterminate_code_or_data`. It deliberately emits an empty
`confirmed_level_data_ranges` collection, regardless of the number of
repeats. No heuristic ranking is evidence of a level map.

Run locally with private traces:

```sh
python3 tools/triage_prg_reads.py private/first_level/stage45_prg_reads.tsv --meta private/first_level/stage45_prg_reads.meta.txt --min-run 2 --out private/first_level/stage48_triage.json
```

Promotion to a verified data source requires same-session CPU execution and
read correlation, opcode/effective-address validation, exact MMC3 mapping
and independent scene/PPU corroboration. Synthetic tests check that no
address-only trace is mislabeled as restored level geometry.
