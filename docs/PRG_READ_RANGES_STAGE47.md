# Stage 47 — contiguous PRG read candidates

`tools/group_prg_read_ranges.py` consumes the same-session stage45 TSV and
**requires** the stage46-compliant metadata. It groups successive mapped
CPU reads that advance by one byte in the same bank and frame. Unknown-bank
reads end a candidate run. Default minimum length is two reads.

```sh
python3 tools/group_prg_read_ranges.py private/first_level/stage45_prg_reads.tsv --meta private/first_level/stage45_prg_reads.meta.txt --min-run 2 --out private/first_level/stage47_ranges.json
```

The resulting ranges are *hypotheses only*. CPU reads include instruction
fetches; grouping does not prove a data table, camera, geometry or loading
routine. Physical mapping remains unknown until MMC3 state is observed.
Repeated address ranges do not establish gameplay purpose. Synthetic tests
cover unknown bank gaps, short ranges, threshold bounds and incomplete logs.
No game ROM or derived art is committed.
